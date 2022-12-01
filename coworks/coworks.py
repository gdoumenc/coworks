import base64
import io
import logging
import os
import traceback
import typing as t
from functools import partial
from http.cookiejar import CookieJar
from inspect import isfunction
from pathlib import Path

import boto3
import dotenv
from flask import Blueprint as FlaskBlueprint
from flask import Flask
from flask import Response
from flask import current_app
from flask import json
from flask.blueprints import BlueprintSetupState
from flask.testing import FlaskClient
from werkzeug.datastructures import ImmutableDict
from werkzeug.datastructures import MultiDict
from werkzeug.datastructures import WWWAuthenticate
from werkzeug.exceptions import Forbidden
from werkzeug.exceptions import HTTPException
from werkzeug.exceptions import InternalServerError
from werkzeug.exceptions import Unauthorized
from werkzeug.routing import Rule

from .globals import request
from .utils import BIZ_BUCKET_HEADER_KEY
from .utils import BIZ_KEY_HEADER_KEY
from .utils import DEFAULT_LOCAL_WORKSPACE
from .utils import HTTP_METHODS
from .utils import add_coworks_routes
from .utils import get_app_workspace
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

        headers = aws_event['headers']
        request_context = aws_event['requestContext']

        method = request_context['httpMethod']
        scheme = headers['x-forwarded-proto']
        stage = request_context['stage']
        path = aws_event['requestContext']['path'][len(stage) + 1:]
        query_string = MultiDict(aws_event['multiValueQueryStringParameters'])

        is_encoded = aws_event.get('isBase64Encoded', False)
        body = aws_event['body']
        if body and is_encoded:
            body = base64.b64decode(body)

        self.aws_environ = {
            'aws_event': aws_event,
            'aws_context': aws_context,
            'aws_query_string': query_string,
            'aws_body': body,
            "wsgi.input": io.BytesIO(b""),
            "wsgi.url_scheme": scheme,
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
        }
        self.cookie_jar = CoworksCookieJar(headers.get('cookie'))

    def open(self, *args, **kwargs):
        req = CoworksRequest(self.aws_environ, populate_request=False, shallow=True)
        return super().open(req)

    def _copy_environ(self, other):
        return {**other}


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

    def __init__(self, name: str = None, **kwargs) -> None:
        """ Initialize a technical microservice.
        :param name: Name used to identify the microservice.
        :param kwargs: Other Chalice parameters.
        """

        # Adds stage variables
        if os.getenv("FLASK_RUN_FROM_CLI"):
            workspace = get_app_workspace()
            project_dir = os.getenv("CWS_PROJECT_DIR", '.')
            for env_filename in (f".env.{workspace}", f".flaskenv.{workspace}"):
                path = dotenv.find_dotenv((Path(project_dir) / env_filename).as_posix(), usecwd=True)
                loaded = dotenv.load_dotenv(path)

        self.default_config = ImmutableDict({
            **self.default_config,
            "FLASK_SKIP_DOTENV": True,
        })

        name = name or self.__class__.__name__.lower()
        super().__init__(import_name=name, static_folder=None, **kwargs)

        self.request_class = CoworksRequest
        self.response_class = CoworksResponse

        self.deferred_init_routes_functions: t.List[t.Callable] = []
        self._cws_app_initialized = False
        self._cws_conf_updated = False

        @self.before_request
        def before():
            self._check_token()

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
        self._init_app(False)

        if os.environ.get("FLASK_RUN_FROM_CLI") == "true":
            self.init_cli()
            for bp in self.blueprints.values():
                if isinstance(bp, Blueprint):
                    t.cast(Blueprint, bp).init_cli(self)

        return super().app_context()

    def cws_client(self, aws_event, aws_context):
        """CoWorks client with new globals.
        """
        self._init_app(False)
        return CoworksClient(self, CoworksResponse, use_cookies=True, aws_event=aws_event, aws_context=aws_context)

    @property
    def routes(self) -> t.List[Rule]:
        """Returns the list of routes defined in the microservice.
        """
        return [r.rule for r in self.url_map.iter_rules()]

    def token_authorizer(self, token: str) -> t.Union[bool, str]:
        """Defined the authorization process.

        If the returned value is False, all routes for all stages are denied.
        If the returned value is True, all routes for all stages are accepted.
        If the returned value is a string, then it must be a stage name and all routes are accepted for this stage.

        By default, no entry are accepted for security reason.
        """

        if get_app_workspace() == DEFAULT_LOCAL_WORKSPACE:
            return True
        return token == os.getenv('TOKEN')

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

        bucket = key = ''
        try:
            bucket = headers.get(self.config['X-CWS-S3Bucket'].lower())
            key = headers.get(self.config['X-CWS-S3Key'].lower())
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

    def _init_app(self, in_lambda):
        """Finalize the app initialization.
        """
        if not self._cws_app_initialized:
            self._update_config(in_lambda=in_lambda)
            add_coworks_routes(self)
            for fun in self.deferred_init_routes_functions:
                fun()

            for bp in self.blueprints.values():
                if isinstance(bp, Blueprint):
                    t.cast(Blueprint, bp).init_app(self)
            self._cws_app_initialized = True

    def __call__(self, arg1, arg2) -> dict:
        """Main microservice entry point.
        """
        in_flask = isfunction(arg2)
        self._init_app(not in_flask)

        # Lambda event call or Flask call
        if in_flask:
            res = self._flask_handler(arg1, arg2)
        else:
            res = self._lambda_handler(arg1, arg2)

        return res

    def _lambda_handler(self, event: t.Dict[str, t.Any], context: t.Dict[str, t.Any]):
        """Lambda handler.
        """
        if event.get('type') == 'TOKEN':
            return self._token_handler(event, context)
        return self._api_handler(event, context)

    def _token_handler(self, aws_event: t.Dict[str, t.Any], aws_context: t.Dict[str, t.Any]) -> dict:
        """Authorization token handler.
        """
        self.logger.warning(f"Calling {self.name} for authorization : {aws_event}")

        try:
            res = self.token_authorizer(aws_event['authorizationToken'])
            self.logger.debug(f"Token authorizer return is : {res}")
            return TokenResponse(res, aws_event['methodArn']).json
        except Exception as e:
            self.logger.error(f"Error in token handler for {self.name} : {e}")
            self.logger.error(''.join(traceback.format_exception(None, e, e.__traceback__)))
            return TokenResponse(False, aws_event['methodArn']).json

    def _api_handler(self, aws_event: t.Dict[str, t.Any], aws_context: t.Dict[str, t.Any]) -> dict:
        """API handler.
        """
        self.logger.warning(f"Calling {self.name} by api : {aws_event}")

        # Transforms as simple client call and manage exception if needed
        try:
            with self.cws_client(aws_event, aws_context) as c:
                resp = c.open()
                resp = self._convert_to_lambda_response(resp)

                # Strores response in S3 if asynchronous call
                invocation_type = aws_event['headers'].get('invocationtype')
                if invocation_type == 'Event':
                    self.store_response(resp, aws_event['headers'])
        except Exception as e:
            if isinstance(e, HTTPException):
                resp = self._structured_error(e)
            else:
                self.logger.error(f"Error in api handler for {self.name} : {e}")
                self.logger.error(''.join(traceback.format_exception(None, e, e.__traceback__)))
                resp = self._structured_error(InternalServerError(original_exception=e))
            self.logger.debug(f"Status code returned by api : {resp.get('statusCode')}")
        else:
            if isinstance(resp, Response):
                self.logger.debug(f"Status code returned by api : {resp.status_code}")

        if self.logger.getEffectiveLevel() == logging.DEBUG:
            content = json.dumps(resp) if type(resp) is dict else resp
            self.logger.debug(f"API returns ({len(content)})")
        return resp

    def _flask_handler(self, environ: t.Dict[str, t.Any], start_response: t.Callable[[t.Any], None]):
        """Flask handler.
        """
        return self.wsgi_app(environ, start_response)

    def _update_config(self, *, in_lambda: bool):
        if not self._cws_conf_updated:
            workspace = get_app_workspace()

            # Set predefined environment variables
            self.config['X-CWS-S3Bucket'] = BIZ_BUCKET_HEADER_KEY
            self.config['X-CWS-S3Key'] = BIZ_KEY_HEADER_KEY

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

    def _convert_to_lambda_response(self, resp):
        """Convert Lambda response."""

        # returns JSON structure
        if resp.is_json:
            try:
                return self._aws_payload(resp.json, resp.status_code, resp.headers)
            except (Exception,):
                resp.mimetype = "text/plain"

        # returns simple string JSON structure
        if resp.mimetype and resp.mimetype.startswith('text'):
            try:
                return self._aws_payload(resp.get_data(True), resp.status_code, resp.headers)
            except ValueError:
                pass

        # returns direct payload
        data = resp.get_data()
        if not isinstance(data, bytes):
            msg = f'Expected bytes type for body with binary Content-Type. Got {type(data)} type body instead.'
            raise ValueError(msg)
        return base64.b64encode(data).decode('ascii')

    def _aws_payload(self, body, status_code, headers):
        return {
            "statusCode": status_code,
            "headers": {k: v for k, v in headers.items()},
            "body": body,
            "isBase64Encoded": False,
        }

    def _structured_error(self, e: HTTPException):
        headers = {'content_type': "application/json"}
        return self._aws_payload(e.description, e.code, headers)
