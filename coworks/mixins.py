import cgi
import inspect
import io
import json
import traceback
import urllib
from functools import update_wrapper, partial

from aws_xray_sdk.core import xray_recorder
from botocore.exceptions import BotoCoreError
from chalice import AuthResponse, BadRequestError, Response
from requests_toolbelt.multipart import MultipartDecoder

from coworks import aws
from coworks.error import CwsError
from .utils import HTTP_METHODS, class_auth_methods, class_http_methods, trim_underscores, make_absolute


class EntryPoint:
    """An entry point is an API entry defined on a component, with a specific authorization function and
    is response function."""

    def __init__(self, component, auth, fun):
        self.component = component
        self.auth = auth
        self.fun = fun


class Entry(dict):

    @property
    def authorizer(self):
        for method in HTTP_METHODS:
            m = self.get(method.upper())
            if m:
                return m.auth

    def call_get(self, *args, **kwargs):
        method = self["GET"]
        return method.fun(method.component, *args, **kwargs)

    def call_post(self, *args, **kwargs):
        method = self["POST"]
        return method.fun(method.component, *args, **kwargs)


class CoworksMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.debug = kwargs.pop('debug', False)

        # A list of functions that will be called at the first activation.
        # To register a function, use the :meth:`before_first_request` decorator.
        self.before_first_activation_funcs = []

        # A list of functions that will be called at the beginning of each activation.
        # To register a function, use the :meth:`before_activation` decorator.
        self.before_activation_funcs = []

        # A list of functions that will be called after each activation.
        # To register a function, use the :meth:`after_activation` decorator.
        self.after_activation_funcs = []

        # A list of functions that will be called in case of exception.
        # To register a function, use the :meth:`handle_exception` decorator.
        self.handle_exception_funcs = []

        self.aws_s3_sfn_data_session = aws.AwsS3Session(env_var_access_key="AWS_RUN_ACCESS_KEY_ID",
                                                    env_var_secret_key="AWS_RUN_SECRET_KEY",
                                                    env_var_region="AWS_RUN_REGION")
        self.aws_s3_form_data_session = aws.AwsS3Session(env_var_access_key="AWS_FORM_DATA_ACCESS_KEY_ID",
                                                     env_var_secret_key="AWS_FORM_DATA_SECRET_KEY",
                                                     env_var_region="AWS_FORM_DATA_REGION")

    def before_first_activation(self, f):
        """Registers a function to be run before the first activation of the microservice.

        May be used as a decorator.

        The function will be called with event and context positional arguments and its return value is ignored.
        """

        self.before_first_activation_funcs.append(f)
        return f

    def before_activation(self, f):
        """Registers a function to called before each activation of the microservice.
        :param f:  Function added to the list.
        :return: None.

        May be used as a decorator.

        The function will be called with event and context positional arguments and its return value is ignored.
        """

        self.before_activation_funcs.append(f)
        return f

    def after_activation(self, f):
        """Registers a function to be called after each activation of the microservice.

        May be used as a decorator.

        The function will be called with the response and its return value is the final response.
        """

        self.after_activation_funcs.append(f)
        return f

    def handle_exception(self, f):
        """Registers a function to be called in case of exception.

        May be used as a decorator.

        The function will be called with the exception and eventually a response to return.
        """

        self.handle_exception_funcs.append(f)
        return f

    def _init_routes(self, app, *, url_prefix='', authorizer=None, hide_routes=None):
        """ Creates all routes for a microservice.
        :param authorizer is the default global authorization function.
        :param hide_routes list of routes to be hidden.
        """

        # Global authorization function may be redefined
        if authorizer is not None:
            auth = authorizer
        else:
            auth_fun = app.config.auth if app.config.auth else class_auth_methods(self)
            auth = self._create_auth_proxy(auth_fun) if auth_fun else None

        # Adds entrypoints
        methods = class_http_methods(self)
        for method, func in methods:

            # Get function's route
            if func.__name__ == method:
                route = f"{url_prefix}"
            else:
                name = func.__name__[len(method) + 1:]
                name = trim_underscores(name)  # to allow several functions with same route but different args
                name = name.replace('_', '/')
                route = f"{url_prefix}/{name}" if url_prefix else f"{name}"
            entry_path = route

            # Get parameters
            args = inspect.getfullargspec(func).args[1:]
            defaults = inspect.getfullargspec(func).defaults
            varkw = inspect.getfullargspec(func).varkw
            if defaults:
                len_defaults = len(defaults)
                for index, arg in enumerate(args[:-len_defaults]):
                    entry_path = entry_path + f"/{{{arg}}}" if entry_path else f"{{{arg}}}"
                    route = route + f"/{{_{index}}}" if route else f"{{_{index}}}"
                kwarg_keys = args[-len_defaults:]
            else:
                for index, arg in enumerate(args):
                    entry_path = entry_path + f"/{{{arg}}}" if entry_path else f"{{{arg}}}"
                    route = route + f"/{{_{index}}}" if route else f"{{_{index}}}"
                kwarg_keys = {}

            proxy = self._create_rest_proxy(func, kwarg_keys, args, varkw)

            # Creates the entry (TODO: autorization may be redefined with decorator)
            route = make_absolute(route)
            app.entries[entry_path][method.upper()] = EntryPoint(self, auth, func)
            if not hide_routes and not getattr(func, '__cws_hidden', False):
                app.route(f"{route}", methods=[method.upper()], authorizer=auth, cors=app.config.cors,
                          content_types=list(app.config.content_type))(proxy)

    def _create_auth_proxy(self, auth_method):

        def proxy(auth_activation):
            subsegment = xray_recorder.current_subsegment()
            try:
                auth = auth_method(self, auth_activation)
                if subsegment:
                    subsegment.put_metadata('result', auth)
            except Exception as e:
                self.logger.info(f"Exception : {str(e)}")
                traceback.print_exc()
                if subsegment:
                    subsegment.add_exception(e, traceback.extract_stack())
                raise BadRequestError(str(e))

            if type(auth) is bool:
                if auth:
                    return AuthResponse(routes=['*'], principal_id='user')
                return AuthResponse(routes=[], principal_id='user')
            elif type(auth) is list:
                return AuthResponse(routes=auth, principal_id='user')
            return auth

        proxy = update_wrapper(proxy, auth_method)
        proxy.__name__ = 'app'
        return self.authorizer(name='auth')(proxy)

    def _create_rest_proxy(self, func, kwarg_keys, args, varkw):
        original_app_class = self.__class__

        def proxy(**kws):
            try:
                # Renames positional parameters (index added in label)
                kwargs = {}
                for kw, value in kws.items():
                    param = args[int(kw[1:])]
                    kwargs[param] = value

                # Adds kwargs parameters
                def check_param_expected_in_lambda(param_name):
                    """Alerts when more parameters than expected are defined in request."""
                    if param_name not in kwarg_keys and varkw is None:
                        raise BadRequestError(f"TypeError: got an unexpected keyword argument '{param_name}'")

                def add_param(param_name, param_value):
                    check_param_expected_in_lambda(param_name)
                    if param_name in params:
                        if isinstance(params[param_name], list):
                            params[param_name].append(param_value)
                        else:
                            params[param_name] = [params[param_name], param_value]
                    else:
                        params[param_name] = param_value

                req = self.current_request
                if kwarg_keys or varkw:
                    params = {}
                    if req.raw_body:  # POST request
                        content_type = req.headers['content-type']
                        if content_type.startswith('multipart/form-data'):
                            try:
                                multipart_decoder = MultipartDecoder(req.raw_body, content_type)
                                for part in multipart_decoder.parts:
                                    name, content = self._get_multipart_content(part)
                                    add_param(name, content)
                            except Exception as e:
                                raise CwsError(str(e))
                            kwargs = dict(**kwargs, **params)
                        elif content_type.startswith('application/x-www-form-urlencoded'):
                            params = urllib.parse.parse_qs(req.raw_body.decode("utf-8"))
                            kwargs = dict(**kwargs, **params)
                        elif content_type.startswith('application/json'):
                            if hasattr(req.json_body, 'items'):
                                params = {}
                                for k, v in req.json_body.items():
                                    add_param(k, v)
                                kwargs = dict(**kwargs, **params)
                            else:
                                kwargs[kwarg_keys[0]] = req.json_body
                        elif content_type.startswith('text/plain'):
                            kwargs[kwarg_keys[0]] = req.json_body
                        else:
                            BadRequestError(f"Cannot manage content type {content_type} for {self}")

                    else:  # GET request

                        # adds parameters from qurey parameters
                        for k in req.query_params or []:
                            value = req.query_params.getlist(k)
                            add_param(k, value if len(value) > 1 else value[0])
                        kwargs = dict(**kwargs, **params)
                else:
                    if not args and (req.raw_body or req.query_params):
                        raise BadRequestError(f"TypeError: got an unexpected arguments")

                # chalice is changing class for local server for threading reason (why not mixin..?)
                self_class = self.__class__
                if self_class != original_app_class:
                    self.__class__ = original_app_class

                resp = func(self, **kwargs)
                self.__class__ = self_class
                return _convert_response(resp)

            except Exception as e:
                subsegment = xray_recorder.current_subsegment()
                if subsegment:
                    subsegment.add_error_flag()
                raise

        proxy = update_wrapper(proxy, func)
        proxy.__cws_func__ = update_wrapper(partial(func, self), func)
        return proxy

    def _get_multipart_content(self, part):
        headers = {k.decode('utf-8'): cgi.parse_header(v.decode('utf-8')) for k, v in part.headers.items()}
        content = part.content
        _, content_disposition_params = headers['Content-Disposition']
        part_content_type, _ = headers.get('Content-Type', (None, None))
        name = content_disposition_params['name']

        # content in a text or json value
        if 'filename' not in content_disposition_params:
            if part_content_type == 'application/json':
                return name, self._get_data_on_s3(json.loads(content.decode('utf-8')))
            return name, self._get_data_on_s3(content.decode('utf-8'))

        # content in a file (s3 or plain text)
        if part_content_type == 'text/s3':
            pathes = content.decode('utf-8').split('/', 1)
            try:
                s3_object = self.aws_s3_form_data_session.client.get_object(Bucket=pathes[0], Key=pathes[1])
            except BotoCoreError:
                return CwsError(f"Bucket={pathes[0]} Key={pathes[1]} not found on s3")
            file = io.BytesIO(s3_object['Body'].read())
            mime_type = s3_object['ContentType']
        else:
            file = io.BytesIO(content)
            mime_type = part_content_type
        file.name = content_disposition_params['filename']

        return name, FileParam(file, mime_type)

    def _set_multipart_content(self, form_data):
        def encode_part(_part):
            if type(_part) is str:
                return None, _part, 'text/plain'

            if 'mime_type' in _part:
                mime_type = _part.get('mime_type')
            elif 'json' in _part:
                _part['content'] = _part.get('json')
                mime_type = 'application/json'
            elif 's3' in _part:
                path = _part.get('s3')
                _part['filename'] = path.split('/')[-1]
                _part['path'] = path
                mime_type = 'text/s3'
            else:
                mime_type = 'text/plain'

            filename = _part.get('filename')
            if mime_type == 'text/plain':
                content = _part.get('content')
                return filename, content, mime_type
            elif mime_type == 'application/json':
                content = _part.get('content')
                return filename, json.dumps(content), mime_type
            elif mime_type == 'text/s3':
                path = _part.get('path')
                return filename, path, mime_type
            else:
                raise BadRequestError(f"Undefined mime type {mime_type}")

        parts = []
        for name, part in form_data.items():
            if type(part) is list:
                parts.extend([(name, encode_part(p)) for p in part])
            else:
                parts.append((name, encode_part(part)))
        return parts

    def _set_data_on_s3(self, data):
        """Saves value on S3 temporary file if content is too big."""

        def set_on_s3(value):
            s3_client = self.aws_s3_sfn_data_session.client
            context = self.lambda_context
            key = f"tmp/{context.aws_request_id}"
            tags = f"Name={context.function_name}"
            s3_client.put_object(Bucket="coworks-microservice", Key=key, Body=value, Tagging=tags)
            return f"$${key}$$"

        if type(data) == str:
            return set_on_s3(data) if len(data) > 1000 else data
        if type(data) == list:
            return [self._set_data_on_s3(v) for v in data]
        if type(data) == dict:
            for k, v in data.items():
                data[k] = self._set_data_on_s3(v)
        return data

    def _get_data_on_s3(self, data):
        """Retrieves value from S3 temporary file (content too big)."""

        def get_on_s3(value):
            s3_client = self.aws_s3_sfn_data_session.client
            s3_object = s3_client.get_object(Bucket="coworks-microservice", Key=value[2:-2])
            return s3_object['Body'].read().decode("utf-8")

        if type(data) == str:
            return get_on_s3(data) if data.startswith('$$') and data.endswith('$$') else data
        if type(data) == list:
            return [self._get_data_on_s3(v) for v in data]
        if type(data) == dict:
            for k, v in data.items():
                data[k] = self._get_data_on_s3(v)
        return data


def _convert_response(resp):
    if type(resp) is tuple:
        if len(resp) == 2:
            if type(resp[1]) is int:
                return Response(body=resp[0], status_code=resp[1])
            elif type(resp[1]) is dict:
                return Response(body=resp[0], status_code=200, headers=resp[1])
            else:
                raise BadRequestError("Internal error (wrong result type)")
        else:
            return Response(body=resp[0], status_code=resp[1], headers=resp[2])

    elif not isinstance(resp, Response):
        return Response(body=resp)

    return resp


class FileParam:

    def __init__(self, file, mime_type):
        self.file = file
        self.mime_type = mime_type

    def __repr__(self):
        if self.mime_type:
            return f'FileParam({self.file.name}, {self.mime_type})'
        return f'FileParam({self.file.name})'
