import base64
import logging
import os
import typing as t
from dataclasses import dataclass
from functools import partial
from inspect import isfunction

from flask import Blueprint as FlaskBlueprint
from flask import Flask
from flask import abort
from flask import current_app
from flask.blueprints import BlueprintSetupState
from flask.ctx import RequestContext
from flask.testing import FlaskClient
from werkzeug.exceptions import HTTPException
from werkzeug.exceptions import InternalServerError
from werkzeug.routing import Rule

from .config import Config
from .config import DEFAULT_DEV_WORKSPACE
from .config import DevConfig
from .config import LocalConfig
from .config import ProdConfig
from .globals import request
from .utils import HTTP_METHODS
from .utils import add_coworks_routes
from .utils import trim_underscores
from .wrappers import ApiResponse
from .wrappers import Request
from .wrappers import TokenResponse


#
# Decorators
#


def entry(fun: t.Callable = None, binary: bool = False, content_type: str = None) -> t.Callable:
    """Decorator to create a microservice entry point from function name."""
    if fun is None:
        if binary and not content_type:
            content_type = 'application/octet-stream'
        return partial(entry, binary=binary, content_type=content_type)

    name = fun.__name__.upper()
    for method in HTTP_METHODS:
        fun.__CWS_METHOD = method
        fun.__CWS_BINARY = binary
        fun.__CWS_CONTENT_TYPE = content_type
        if name == method:
            fun.__CWS_PATH = ''
            return fun
        if name.startswith(f'{method}_'):
            name = fun.__name__[len(method) + 1:]
            name = trim_underscores(name)  # to allow several functions with different args
            fun.__CWS_PATH = name.replace('_', '/')
            return fun
    raise AttributeError(f"The function name {fun.__name__} doesn't start with a HTTP method name.")


def hide(fun: t.Callable) -> t.Callable:
    """Hide a route of the microservice.

     May be used as a decorator.

     Usefull when creating inherited microservice.
     """

    setattr(fun, '__cws_hidden', True)
    return fun


#
# Classes
#


@dataclass
class ScheduleEntry:
    """An schedule entry is an EventBridge entry defined on a microservice, with the schedule expression,
    its description and its response function."""

    name: str
    exp: str
    desc: str
    fun: t.Callable


class CoworksClient(FlaskClient):
    """Redefined to force mimetype to be 'text/plain' in case of string return.
    """

    def __init__(self, *args: t.Any, aws_event=None, aws_context=None, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)
        self.environ_base.update({
            "aws_event": aws_event,
            "aws_context": aws_context,
        })


class Blueprint(FlaskBlueprint):
    """ Represents a blueprint, list of routes that will be added to microservice when registered.

    See :ref:`Blueprint <blueprint>` for more information.
    """

    def __init__(self, name: str = None, **kwargs):
        """Initialize a blueprint.

        :param kwargs: Other Flask blueprint parameters.

        """
        import_name = self.__class__.__name__.lower()
        super().__init__(name or import_name, import_name, **kwargs)

    @property
    def logger(self) -> logging.Logger:
        return current_app.logger

    def make_setup_state(self, app: "TechMicroService", options: t.Dict, *args) -> BlueprintSetupState:
        """Stores creation state for deferred initialization."""
        state = super().make_setup_state(app, options, *args)

        # Defer blueprint route initialization.
        if not options.get('hide_routes', False):
            app.deferred_init_routes_functions.append(partial(add_coworks_routes, state.app, state))

        return state


class TechMicroService(Flask):
    """Simple tech microservice.
    
    See :ref:`tech` for more information.
    """

    def __init__(self, name: str = None, *, configs: t.Union[Config, t.List[Config]] = None, **kwargs) -> None:
        """ Initialize a technical microservice.
        :param name: Name used to identify the microservice.
        :param configs: Deployment configurations.
        :param kwargs: Other Chalice parameters.
        """
        name = name or self.__class__.__name__.lower()

        self.configs = configs or [LocalConfig(), DevConfig(), ProdConfig()]
        if type(self.configs) is not list:
            self.configs = [configs]

        super().__init__(import_name=name, static_folder=None, **kwargs)

        self.test_client_class = CoworksClient
        self.request_class = Request
        self.response_class = ApiResponse

        self.any_token_authorized = False
        self.deferred_init_routes_functions: t.List[t.Callable] = []
        self._cws_app_initialized = False
        self._cws_conf_updated = False

        @self.before_request
        def check_token():
            if not request.in_lambda_context:
                token = request.headers.get('Authorization', self.config.get('DEFAULT_TOKEN'))
                if token is None:
                    abort(401)
                valid = self.token_authorizer(token)
                if not valid:
                    abort(403)

    def app_context(self):
        """Override to initialize coworks microservice."""
        if not self._cws_app_initialized:
            add_coworks_routes(self)
            for fun in self.deferred_init_routes_functions:
                fun()
            self._cws_app_initialized = True
        return super().app_context()

    def request_context(self, environ: dict) -> RequestContext:
        """Redefined to :
        - initialize the environment
        - add Lambda event and context in globals.
        """
        ctx = super().request_context(environ)
        ctx.aws_event = environ.get('aws_event')
        ctx.aws_context = environ.get('aws_context')
        return ctx

    def cws_client(self, event, context):
        """CoWorks client with new globals."""
        return super().test_client(aws_event=event, aws_context=context)

    def test_client(self, *args, **kwargs):
        """This client must be used only for testing."""
        self.testing = True
        return super().test_client(*args, **kwargs)

    @property
    def ms_type(self) -> str:
        return 'tech'

    @property
    def routes(self) -> t.List[Rule]:
        """Returns the list of routes defined in the microservice."""
        return [r.rule for r in self.url_map.iter_rules()]

    def get_config(self, workspace) -> Config:
        """Returns the configuration corresponding to the workspace."""
        for conf in self.configs:
            if conf.is_valid_for(workspace):
                return conf
        return Config()

    def token_authorizer(self, token: str) -> t.Union[bool, str]:
        """Defined the authorization process.

        If the returned value is False, all routes for all stages are denied.
        If the returned value is True, all routes for all stages are accepted.
        If the returned value is a string, then it must be a stage name and all routes are accepted for this stage.

        By default no entry are accepted for security reason.
        """

        return self.any_token_authorized

    def base64decode(self, data):
        """Base64 decode function used for lambda interaction."""
        if not isinstance(data, bytes):
            data = data.encode('ascii')
        output = base64.b64decode(data)
        return output

    def base64encode(self, data):
        """Base64 encode function used for lambda interaction."""
        if not isinstance(data, bytes):
            msg = f'Expected bytes type for body with binary Content-Type. Got {type(data)} type body instead.'
            raise ValueError(msg)
        data = base64.b64encode(data).decode('ascii')
        return data

    def __call__(self, arg1, arg2) -> dict:
        """Main microservice entry point."""

        # Lambda event call or Flask call
        if isfunction(arg2):
            res = self._flask_handler(arg1, arg2)
        else:
            res = self._lambda_handler(arg1, arg2)

        # res['headers']['x-cws-workspace'] = os.getenv('WORKSPACE')

        return res

    def _lambda_handler(self, event: t.Dict[str, t.Any], context: t.Dict[str, t.Any]):
        """Lambda handler.
        """
        self.logger.debug(f"Event: {event}")
        self.logger.debug(f"Context: {context}")

        self._update_config(load_env=False)
        if event.get('type') == 'TOKEN':
            return self._token_handler(event, context)
        return self._api_handler(event, context)

    def _token_handler(self, event: t.Dict[str, t.Any], context: t.Dict[str, t.Any]) -> dict:
        """Authorization token handler.
        """
        self.logger.debug(f"Calling {self.name} for authorization : {event}")

        try:
            res = self.token_authorizer(event['authorizationToken'])
            return TokenResponse(res, event['methodArn']).json
        except Exception as e:
            self.logger.debug(f"Error in token handler for {self.name} : {e}")
            return TokenResponse(False, event['methodArn']).json

    def _api_handler(self, event: t.Dict[str, t.Any], context: t.Dict[str, t.Any]) -> dict:
        """API handler.
        """
        self.logger.debug(f"Calling {self.name} by api : {event}")

        def full_path():
            url = event['path']

            # Replaces route parameters
            url = url.format(url, **event['params']['path'])

            # Adds query parameters
            params = event['multiValueQueryStringParameters']
            if params:
                url += '?'
                for i, (k, v) in enumerate(params.items()):
                    if i:
                        url += '&'
                    for j, vl in enumerate(v):
                        if j:
                            url += '&'
                        url += f"{k}={vl}"
            return url

        # Transform as simple client call and manage exception if needed
        try:
            with self.cws_client(event, context) as c:
                method = event['httpMethod']
                kwargs = self._get_kwargs(event)
                resp = getattr(c, method.lower())(full_path(), **kwargs)
                return self._convert_to_lambda_response(resp)
        except Exception as e:
            error = e if isinstance(e, HTTPException) else InternalServerError(original_exception=e)
            return self._structured_error(error)

    def _flask_handler(self, environ: t.Dict[str, t.Any], start_response: t.Callable[[t.Any], None]):
        """Flask handler.
        """

        self._update_config(load_env=True)
        return self.wsgi_app(environ, start_response)

    def _update_config(self, load_env: bool):
        if not self._cws_conf_updated:
            workspace = os.environ.get('WORKSPACE', DEFAULT_DEV_WORKSPACE)
            config = self.get_config(workspace)
            self.config['WORKSPACE'] = config.workspace
            self.config['DEFAULT_TOKEN'] = config.default_token
            if load_env:
                config.load_environment_variables(self.root_path)
            self._cws_conf_updated = True

    def _get_kwargs(self, event):
        def is_json(mt):
            return (
                    mt == "application/json"
                    or type(mt) is str
                    and mt.startswith("application/")
                    and mt.endswith("+json")
            )

        kwargs = {}
        content_type = event['headers'].get('content-type')
        if content_type:
            kwargs['content_type'] = content_type

        method = event['httpMethod']
        if method not in ['PUT', 'POST']:
            return kwargs

        is_encoded = event.get('isBase64Encoded', False)
        body = event['body']
        if body and is_encoded:
            body = self.base64decode(body)
        self.logger.debug(f"Body: {body}")

        if is_json(content_type):
            kwargs['json'] = body
            return kwargs
        kwargs['data'] = body
        return kwargs

    def _convert_to_lambda_response(self, resp):
        """Convert Lambda response."""

        # returns JSON structure
        if resp.is_json:
            try:
                return self._structured_payload(resp.json, resp.status_code, resp.headers)
            except (Exception,):
                resp.mimetype = "text/plain"

        # returns simple string JSON structure
        if resp.mimetype.startswith('text'):
            try:
                return self._structured_payload(resp.get_data(True), resp.status_code, resp.headers)
            except ValueError:
                pass

        # returns direct payload
        return self.base64encode(resp.get_data())

    def _structured_payload(self, body, status_code, headers):
        return {
            "statusCode": status_code,
            "headers": {k: v for k, v in headers.items()},
            "body": body,
            "isBase64Encoded": False,
        }

    def _structured_error(self, e: HTTPException):
        headers = {'content_type': "application/json"}
        return self._structured_payload(e.description, e.code, headers)

    def schedule(self, *args, **kwargs):
        raise Exception("Schedule decorator is defined on BizMicroService, not on TechMicroService")


class BizMicroService(TechMicroService):
    """Biz composed microservice activated by events.
    """
