import importlib
import inspect
import os
import platform
import sys
import traceback
import typing as t
from functools import partial
from functools import update_wrapper

import click
import dotenv
from flask import current_app
from flask import make_response
from flask.blueprints import BlueprintSetupState
from werkzeug.exceptions import HTTPException
from werkzeug.exceptions import InternalServerError
from werkzeug.exceptions import UnprocessableEntity

from .globals import request

if t.TYPE_CHECKING:
    from flask.scaffold import Scaffold

HTTP_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS']

PROJECT_CONFIG_VERSION = 3

DEFAULT_DEV_STAGE = "dev"
DEFAULT_LOCAL_STAGE = "local"
DEFAULT_PROJECT_DIR = "tech"

BIZ_BUCKET_HEADER_KEY: str = 'X-CWS-S3Bucket'
BIZ_KEY_HEADER_KEY: str = 'X-CWS-S3Key'


def add_coworks_routes(app, bp_state: BlueprintSetupState = None) -> None:
    """ Creates all routes for a microservice.
    :param app the app microservice
    :param bp_state the blueprint state
    """
    # Adds entrypoints
    stage = get_app_stage()
    scaffold = bp_state.blueprint if bp_state else app
    method_members = inspect.getmembers(scaffold.__class__, lambda x: inspect.isfunction(x))
    methods = [fun for _, fun in method_members if hasattr(fun, '__CWS_METHOD')]
    for fun in methods:

        # the entry is not defined for this stage
        stages = getattr(fun, '__CWS_STAGES')
        if stages and stage not in stages:
            continue

        method = getattr(fun, '__CWS_METHOD')
        entry_path = path_join(getattr(fun, '__CWS_PATH'))

        # Get parameters
        args = inspect.getfullargspec(fun).args[1:]
        defaults = inspect.getfullargspec(fun).defaults
        varkw = inspect.getfullargspec(fun).varkw
        if defaults:
            len_defaults = len(defaults)
            for index, arg in enumerate(args[:-len_defaults]):
                entry_path = path_join(entry_path, f"/<{arg}>")
            kwarg_keys = args[-len_defaults:]
        else:
            for index, arg in enumerate(args):
                entry_path = path_join(entry_path, f"/<{arg}>")
            kwarg_keys = {}

        proxy = create_cws_proxy(scaffold, fun, kwarg_keys, args, varkw)
        proxy.__CWS_BINARY_HEADERS = getattr(fun, '__CWS_BINARY_HEADERS')
        proxy.__CWS_NO_AUTH = getattr(fun, '__CWS_NO_AUTH')
        proxy.__CWS_NO_CORS = getattr(fun, '__CWS_NO_CORS')
        proxy.__CWS_FROM_BLUEPRINT = bp_state.blueprint.name if bp_state else None

        prefix = f"{bp_state.blueprint.name}." if bp_state else ''
        endpoint = f"{prefix}{fun.__name__}"

        # Creates the entry
        url_prefix = bp_state.url_prefix if bp_state else ''
        rule = make_absolute(entry_path, url_prefix)
        for r in app.url_map.iter_rules():
            if r.rule == rule and method in r.methods:
                raise AssertionError(f"Duplicate route {rule}")

        try:
            app.add_url_rule(rule=rule, view_func=proxy, methods=[method], endpoint=endpoint, strict_slashes=False)
        except AssertionError:
            raise


def create_cws_proxy(scaffold: "Scaffold", func, kwarg_keys, args, varkw):
    def proxy(**kwargs):
        # Adds kwargs parameters
        def check_keyword_expected_in_lambda(param_name):
            """Alerts when more parameters than expected are defined in request."""
            if param_name not in kwarg_keys and varkw is None:
                _err_msg = f"TypeError: got an unexpected keyword argument '{param_name}'"
                raise UnprocessableEntity(_err_msg)

        def as_fun_params(values: dict, flat=True):
            """Set parameters as simple value or list of values if multiple defined.
           :param values: Dict of values.
           :param flat: If set to True the list values of lenth 1 is retrun as single value.
            """
            params = {}
            for k, v in values.items():
                check_keyword_expected_in_lambda(k)
                params[k] = v[0] if flat and len(v) == 1 else v
            return params

        try:
            # Get keyword arguments from request
            if kwarg_keys or varkw:

                # adds parameters from query parameters
                if request.method == 'GET':
                    data = request.values.to_dict(False)
                    kwargs = dict(**kwargs, **as_fun_params(data))

                # Adds parameters from body parameter
                elif request.method in ['POST', 'PUT', 'DELETE']:
                    try:
                        if request.is_json:
                            data = request.get_data()
                            if not data:
                                kwargs = {**kwargs}
                            else:
                                data = request.json
                                if type(data) is dict:
                                    kwargs = dict(**kwargs, **as_fun_params(data, False))
                                else:
                                    kwargs[kwarg_keys[0]] = data
                        elif request.is_multipart:
                            data = request.form.to_dict(False)
                            files = request.files.to_dict(False)
                            kwargs = dict(**kwargs, **as_fun_params(data), **as_fun_params(files))
                        elif request.is_form_urlencoded:
                            data = request.form.to_dict(False)
                            kwargs = dict(**kwargs, **as_fun_params(data))
                        else:
                            data = request.values.to_dict(False)
                            kwargs = dict(**kwargs, **as_fun_params(data))
                    except Exception as e:
                        raise UnprocessableEntity(str(e))

                else:
                    err_msg = f"Keyword arguments are not permitted for {request.method} method."
                    raise UnprocessableEntity(err_msg)

            else:
                if not args:
                    try:
                        if request.content_length:
                            if request.is_json and request.json:
                                err_msg = f"TypeError: got an unexpected arguments (body: {request.json})"
                                raise UnprocessableEntity(err_msg)
                        if request.query_string:
                            err_msg = f"TypeError: got an unexpected arguments (query: {request.query_string})"
                            raise UnprocessableEntity(err_msg)
                    except Exception as e:
                        current_app.logger.error(f"Should not go here (1) : {str(e)}")
                        current_app.logger.error(f"Should not go here (2) : {request.get_data()}")
                        current_app.logger.error(f"Should not go here (3) : {kwargs}")
                        raise

            kwargs = as_typed_kwargs(func, kwargs)
            result = func(scaffold, **kwargs)
            resp = make_response(result) if result is not None else \
                make_response("", 204, {'content-type': 'text/plain'})

            if func.__CWS_BINARY_HEADERS and not request.in_lambda_context:
                resp.headers.update(func.__CWS_BINARY_HEADERS)
        except HTTPException as e:
            try:
                return current_app.handle_user_exception(e)
            except (Exception,):
                resp = make_response(e.description, e.code, {'content-type': 'text/plain'})
        except Exception as e:
            current_app.logger.error(''.join(traceback.format_exception(None, e, e.__traceback__)))
            resp = make_response(str(e), InternalServerError.code, {'content-type': 'text/plain'})

        return resp

    return update_wrapper(proxy, func)


def import_attr(module, attr: str):
    if type(attr) is not str:
        raise AttributeError(f"{attr} is not a string.")
    app_module = importlib.import_module(module)
    if "PYTEST_CURRENT_TEST" in os.environ:
        app_module = importlib.reload(app_module)
    return getattr(app_module, attr)


def class_auth_methods(obj):
    """Returns the auth method from the class if exists."""
    methods = inspect.getmembers(obj.__class__, lambda x: inspect.isfunction(x))

    for name, func in methods:
        if name == 'auth':
            function_is_static = isinstance(inspect.getattr_static(obj.__class__, func.__name__), staticmethod)
            if function_is_static:
                return func
            return partial(func, obj)
    return None


def class_attribute(obj, name: str = None, defaut=None):
    """Returns the list of attributes from the class or the attribute if name parameter is defined
    or default value if not found."""
    attributes = inspect.getmembers(obj.__class__, lambda x: not inspect.isroutine(x))

    if not name:
        return attributes

    filtered = [a[1] for a in attributes if a[0] == name]
    return filtered[0] if filtered else defaut


def path_join(*args):
    """ Joins given arguments into an entry route.
    Slashes are stripped for each argument.
    """

    reduced = [x.lstrip('/').rstrip('/') for x in args if x]
    return '/'.join([x for x in reduced if x])


def make_absolute(route, url_prefix):
    """Creates an absolute route without trailing slash.
    """
    route = route.lstrip('/').rstrip('/')
    if url_prefix:
        prefix = url_prefix.lstrip('/').rstrip('/')
        if route:
            return '/' + prefix + '/' + route
        return '/' + prefix
    return '/' + route


def trim_underscores(name):
    while name.startswith('_'):
        name = name[1:]
    while name.endswith('_'):
        name = name[:-1]
    return name


def get_system_info():
    from flask import __version__ as flask_version

    flask_info = f"flask {flask_version}"
    python_info = f"python {sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}"
    platform_system = platform.system().lower()
    platform_release = platform.release()
    platform_info = f"{platform_system} {platform_release}"
    return f"{flask_info}, {python_info}, {platform_info}"


def as_typed_kwargs(func, kwargs):
    def get_typed_value(tp, val):
        origin = t.get_origin(tp)
        if origin is None:
            if tp is bool:
                return val.lower() in ['true', '1', 'yes']
            return tp(val)
        if origin is list:
            arg = t.get_args(tp)[0]
            if type(val) is list:
                return [arg(v) for v in val]
            return [arg(val)]
        if origin is t.Union:
            for arg in t.get_args(tp):
                try:
                    return get_typed_value(arg, val)
                except (TypeError, ValueError):
                    pass
            raise TypeError()

    typed_kwargs = {**kwargs}
    try:
        hints = t.get_type_hints(func)
        for name, value in kwargs.items():
            try:
                typed_kwargs[name] = get_typed_value(hints.get(name), value)
            except (TypeError, ValueError):
                pass
    except (Exception,):
        pass
    return typed_kwargs


def is_json(mt):
    """Checks if a mime type is json.
    """
    return (
            mt == "application/json"
            or type(mt) is str
            and mt.startswith("application/")
            and mt.endswith("+json")
    )


def get_app_stage():
    return os.getenv('CWS_STAGE', DEFAULT_DEV_STAGE)


def get_app_debug():
    return os.getenv('FLASK_DEBUG')


def load_dotenv(stage: str, as_dict: bool = False):
    loaded = True
    for env_filename in get_env_filenames(stage):
        path = dotenv.find_dotenv(env_filename, usecwd=True)
        if path:
            loaded = loaded and dotenv.load_dotenv(path, override=True)
    return loaded


def load_dotvalues(stage: str):
    environment_variables = {}
    for env_filename in get_env_filenames(stage):
        path = dotenv.find_dotenv(env_filename, usecwd=True)
        if path:
            environment_variables.update(dotenv.dotenv_values(path))
    return environment_variables


def get_env_filenames(stage):
    return [".env", ".flaskenv", f".env.{stage}", f".flaskenv.{stage}"]


def show_stage_banner():
    click.echo(f" * Stage: {get_app_stage()}")
