import base64
import io
import logging
import os
import typing as t
from functools import partial
from http.cookiejar import CookieJar
from inspect import isfunction
from pathlib import Path

import boto3
import click
from flask import Blueprint as FlaskBlueprint
from flask import Flask
from flask import current_app
from flask import json
from flask.blueprints import BlueprintSetupState
from flask.ctx import RequestContext
from flask.testing import FlaskClient
from werkzeug.datastructures import ImmutableDict
from werkzeug.datastructures import WWWAuthenticate
from werkzeug.exceptions import Forbidden
from werkzeug.exceptions import HTTPException
from werkzeug.exceptions import InternalServerError
from werkzeug.exceptions import Unauthorized
from werkzeug.routing import Rule

from .config import Config
from .config import DEFAULT_DEV_WORKSPACE
from .config import DEFAULT_LOCAL_WORKSPACE
from .config import DevConfig
from .config import LocalConfig
from .config import ProdConfig
from .globals import request
from .utils import HTTP_METHODS
from .utils import add_coworks_routes
from .utils import is_json
from .utils import trim_underscores
from .wrappers import CoworksRequest
from .wrappers import CoworksResponse
from .wrappers import TokenResponse


#
# Decorators
#


def entry(fun: t.Callable = None, binary: bool = False, content_type: str = None,
          no_auth: bool = False, no_cors: bool = True) -> t.Callable:
    """Decorator to create a microservice entry point from function name.
    :param fun: the entry function.
    :param binary: allow payload without transformation.
    :param content_type: force default content-type.
    :param no_auth: set authorizer by default.
    :param no_cors: set CORS by default.
    """
    if fun is None:
        if binary and not content_type:
            content_type = 'application/octet-stream'
        return partial(entry, binary=binary, content_type=content_type, no_auth=no_auth, no_cors=no_cors)

    def get_path(start):
        name_ = fun.__name__[start:]
        name_ = trim_underscores(name_)  # to allow several functions with d, Falseifferent args
        return name_.replace('_', '/')

    name = fun.__name__.upper()
    for method in HTTP_METHODS:
        if name == method:
            path = ''
            break
        if name.startswith(f'{method}_'):
            path = get_path(len(f'{method}_'))
            break
    else:
        method = 'POST'
        path = get_path(0)

    fun.__CWS_METHOD = method
    fun.__CWS_PATH = path
    fun.__CWS_BINARY = binary
    fun.__CWS_CONTENT_TYPE = content_type
    fun.__CWS_NO_AUTH = no_auth
    fun.__CWS_NO_CORS = no_cors

    return fun


#
# Classes
#


class CoworksCookieJar(CookieJar):
    """A cookielib.CookieJar modified to inject cookie headers from event.
    """

    def __init__(self, cookies):
        super().__init__()
        self.cookies = cookies

    def inject_wsgi(self, environ):
        """Inject the cookies as client headers into the server's wsgi
        environment.
        """
        environ["HTTP_COOKIE"] = self.cookies

    def extract_wsgi(self, environ, headers):
        pass


class CoworksClient(FlaskClient):
    """Creates environment and complete request.
    """

    def __init__(self, *args: t.Any, aws_event=None, aws_context=None, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)
        self.environ_base.update({
            "aws_event": aws_event,
            "aws_context": aws_context,
        })

        # Complete request content from lambda event
        if aws_event and 'headers' in aws_event:
            headers = aws_event['headers']
            self.cookie_jar = CoworksCookieJar(headers.get('cookie'))


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

    def init_app(self, app):
        ...

    def init_cli(self, app):
        ...

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
        self.default_config = ImmutableDict({
            **self.default_config,
            "JSON_SORT_KEYS": False,
        })

        self.configs = configs or [LocalConfig(), DevConfig(), ProdConfig()]
        if type(self.configs) is not list:
            self.configs = [configs]

        name = name or self.__class__.__name__.lower()
        super().__init__(import_name=name, static_folder=None, **kwargs)

        self.test_client_class = CoworksClient
        self.request_class = CoworksRequest
        self.response_class = CoworksResponse

        self.deferred_init_routes_functions: t.List[t.Callable] = []
        self._cws_app_initialized = False
        self._cws_conf_updated = False

        @self.before_request
        def before():
            self._check_token()
        #     rp = request.path
        #     if rp != '/' and rp.endswith('/'):
        #         msg = "Trailing slash avalaible only on deployed version"
        #         self.logger.error(msg)
        #         raise HTTPException(msg)

    def init_app(self):
        """Called to finalize the application initialization.
        Mainly to get external variables defined specifically for a workspace.
        """

    def init_cli(self):
        """Called only on cli command.
        Mainly externalized to allow specific import not needed on deployed implementation.
        """
        ...

    def app_context(self):
        """Override to initialize coworks microservice.
        """
        self._init_app(True)

        if os.environ.get("FLASK_RUN_FROM_CLI") == "true":
            self.init_cli()
            for bp in self.blueprints.values():
                if isinstance(bp, Blueprint):
                    t.cast(Blueprint, bp).init_cli(self)

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
        """CoWorks client with new globals.
        """
        return super().test_client(aws_event=event, aws_context=context)

    def test_client(self, *args, workspace=DEFAULT_LOCAL_WORKSPACE, **kwargs):
        """This client must be used only for testing.
        """
        self.testing = True
        self._init_app(True, workspace=workspace)

        return super().test_client(*args, **kwargs)

    @property
    def ms_type(self) -> str:
        return 'tech'

    @property
    def routes(self) -> t.List[Rule]:
        """Returns the list of routes defined in the microservice.
        """
        return [r.rule for r in self.url_map.iter_rules()]

    def get_config(self, workspace) -> Config:
        """Returns the configuration corresponding to the workspace.
        """
        for conf in self.configs:
            if conf.is_valid_for(workspace):
                return conf
        return Config()

    def token_authorizer(self, token: str) -> t.Union[bool, str]:
        """Defined the authorization process.

        If the returned value is False, all routes for all stages are denied.
        If the returned value is True, all routes for all stages are accepted.
        If the returned value is a string, then it must be a stage name and all routes are accepted for this stage.

        By default, no entry are accepted for security reason.
        """

        workspace = self.config['WORKSPACE']
        if workspace == DEFAULT_LOCAL_WORKSPACE:
            return True
        return token == os.getenv('TOKEN')

    def base64decode(self, data):
        """Base64 decode function used for lambda interaction.
        """
        if not isinstance(data, bytes):
            data = data.encode('ascii')
        output = base64.b64decode(data)
        return output

    def base64encode(self, data):
        """Base64 encode function used for lambda interaction.
        """
        if not isinstance(data, bytes):
            msg = f'Expected bytes type for body with binary Content-Type. Got {type(data)} type body instead.'
            raise ValueError(msg)
        data = base64.b64encode(data).decode('ascii')
        return data

    def auto_find_instance_path(self):
        """Instance path may be redefined by an environment variable.
        """
        instance_relative_path = os.getenv('INSTANCE_RELATIVE_PATH', '')
        path = Path(self.root_path) / instance_relative_path
        return path.as_posix()

    def store_response(self, resp, headers):
        """Store microservice response in S3 for biz task sequence.

        May be redefined for another storage in asynchronous call.
        """

        bucket = headers.get(self.config['X-CWS-S3Bucket'].lower())
        key = headers.get(self.config['X-CWS-S3Key'].lower())
        try:
            if bucket and key:
                aws_s3_session = boto3.session.Session()
                content = json.dumps(resp) if type(resp) is dict else resp
                buffer = io.BytesIO(content.encode())
                buffer.seek(0)
                self.logger.debug(f"Store response in s3://{bucket}/{key}")
                aws_s3_session.client('s3').upload_fileobj(buffer, bucket, key)
                self.logger.debug(f"Storing response in {bucket}/{key}")
        except Exception as e:
            self.logger.error(f"Exception when storing response in {bucket}/{key} : {str(e)}")

    def _init_app(self, load_env, workspace=None):
        """Finalize the app initialization.
        """
        if not self._cws_app_initialized:
            self._update_config(load_env=load_env, workspace=workspace)
            add_coworks_routes(self)
            for fun in self.deferred_init_routes_functions:
                fun()

            self.init_app()
            for bp in self.blueprints.values():
                if isinstance(bp, Blueprint):
                    t.cast(Blueprint, bp).init_app(self)
            self._cws_app_initialized = True

    def __call__(self, arg1, arg2) -> dict:
        """Main microservice entry point.
        """
        in_flask = isfunction(arg2)
        self._init_app(in_flask)

        # Lambda event call or Flask call
        if in_flask:
            res = self._flask_handler(arg1, arg2)
        else:
            res = self._lambda_handler(arg1, arg2)

        return res

    def _lambda_handler(self, event: t.Dict[str, t.Any], context: t.Dict[str, t.Any]):
        """Lambda handler.
        """
        self.logger.debug(f"Event: {event}")
        self.logger.debug(f"Context: {context}")

        if event.get('type') == 'TOKEN':
            return self._token_handler(event, context)
        return self._api_handler(event, context)

    def _token_handler(self, event: t.Dict[str, t.Any], context: t.Dict[str, t.Any]) -> dict:
        """Authorization token handler.
        """
        self.logger.debug(f"Calling {self.name} for authorization : {event}")

        try:
            res = self.token_authorizer(event['authorizationToken'])
            self.logger.debug(f"Token authorizer return is : {res}")
            return TokenResponse(res, event['methodArn']).json
        except Exception as e:
            self.logger.error(f"Error in token handler for {self.name} : {e}")
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

        # Transforms as simple client call and manage exception if needed
        try:
            with self.cws_client(event, context) as c:
                method = event['httpMethod']
                kwargs = self._get_kwargs(event)
                resp = getattr(c, method.lower())(full_path(), **kwargs)
                resp = self._convert_to_lambda_response(resp)

                # Strores response in S3 if asynchronous call
                invocation_type = event['headers'].get('invocationtype')
                if invocation_type == 'Event':
                    self.store_response(resp, event['headers'])
                else:
                    return resp
        except Exception as e:
            self.logger.error(f"Error in api handler for {self.name} : {e}")
            error = e if isinstance(e, HTTPException) else InternalServerError(original_exception=e)
            return self._structured_error(error)

    def _flask_handler(self, environ: t.Dict[str, t.Any], start_response: t.Callable[[t.Any], None]):
        """Flask handler.
        """

        return self.wsgi_app(environ, start_response)

    def _update_config(self, *, load_env: bool, workspace: str):
        if not self._cws_conf_updated:
            workspace = workspace or os.environ.get('WORKSPACE', DEFAULT_DEV_WORKSPACE)
            if workspace == DEFAULT_LOCAL_WORKSPACE:
                click.echo(f" * Workspace: {workspace}")
            config = self.get_config(workspace)
            self.config['WORKSPACE'] = config.workspace
            self.config['X-CWS-S3Bucket'] = config.bizz_bucket_header_key
            self.config['X-CWS-S3Key'] = config.bizz_key_header_key
            if load_env:
                config.load_environment_variables(self)
            self._cws_conf_updated = True

    def _check_token(self):
        if not request.in_lambda_context:

            # Get no_auth option for this entry
            no_auth = False
            if request.url_rule:
                view_function = self.view_functions.get(request.url_rule.endpoint, None)
                if view_function:
                    no_auth = getattr(view_function, '__CWS_NO_AUTH', False)

            # Checks token if authorization needed
            if not no_auth:
                token = request.headers.get('Authorization', self.config.get('DEFAULT_TOKEN'))
                if token is None:
                    raise Unauthorized(www_authenticate=WWWAuthenticate(auth_type="basic"))
                valid = self.token_authorizer(token)
                if not valid:
                    raise Forbidden()

    def _get_kwargs(self, event):
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


class BizMicroService(TechMicroService):
    """Biz composed microservice activated by events.
    """
