import importlib
import inspect
import os
import platform
import sys
import traceback
import typing as t
from functools import partial
from functools import update_wrapper

from flask import current_app
from flask import make_response
from flask.blueprints import BlueprintSetupState
from werkzeug.datastructures import Headers
from werkzeug.exceptions import BadRequest, HTTPException
from werkzeug.exceptions import BadRequestKeyError

from .globals import request
from .wrappers import CoworksResponse

if t.TYPE_CHECKING:
    from flask.scaffold import Scaffold

HTTP_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS']


def add_coworks_routes(app, bp_state: BlueprintSetupState = None) -> None:
    """ Creates all routes for a microservice.
    :param app the app microservice
    :param bp_state the blueprint state
    """
    # Adds entrypoints
    scaffold = bp_state.blueprint if bp_state else app
    method_members = inspect.getmembers(scaffold.__class__, lambda x: inspect.isfunction(x))
    methods = [fun for _, fun in method_members if hasattr(fun, '__CWS_METHOD')]
    for fun in methods:
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

        proxy = create_rest_proxy(scaffold, fun, kwarg_keys, args, varkw)
        proxy.__CWS_BINARY = getattr(fun, '__CWS_BINARY')
        attr = getattr(fun, '__CWS_CONTENT_TYPE')
        proxy.__CWS_CONTENT_TYPE = attr
        proxy.__CWS_NO_AUTH = getattr(fun, '__CWS_NO_AUTH')
        proxy.__CWS_NO_CORS = getattr(fun, '__CWS_NO_CORS')
        proxy.__CWS_FROM_BLUEPRINT = bp_state.blueprint.name if bp_state else None

        # Creates the entry
        url_prefix = bp_state.url_prefix if bp_state else ''
        rule = make_absolute(entry_path, url_prefix)
        for r in app.url_map.iter_rules():
            if r.rule == rule and method in r.methods:
                raise AssertionError(f"Duplicate route {rule}")

        prefix = f"{bp_state.blueprint.name}." if bp_state else ''
        endpoint = f"{prefix}{fun.__name__}"

        try:
            app.add_url_rule(rule=rule, view_func=proxy, methods=[method], endpoint=endpoint, strict_slashes=False)
        except AssertionError:
            raise


def create_rest_proxy(scaffold: "Scaffold", func, kwarg_keys, args, varkw):
    def proxy(**kwargs):
        try:
            # Adds kwargs parameters
            def check_param_expected_in_lambda(param_name):
                """Alerts when more parameters than expected are defined in request."""
                if param_name not in kwarg_keys and varkw is None:
                    _err_msg = f"TypeError: got an unexpected keyword argument '{param_name}'"
                    current_app.logger.info(_err_msg)
                    raise BadRequestKeyError(_err_msg)

            def as_fun_params(values: dict, flat=True):
                """Set parameters as simple value or list of values if multiple defined.
               :param values: Dict of values.
               :param flat: If set to True the list values of lenth 1 is retrun as single value.
                """
                params = {}
                for k, v in values.items():
                    check_param_expected_in_lambda(k)
                    params[k] = v[0] if flat and len(v) == 1 else v
                return params

            # Get keyword arguments from request
            if kwarg_keys or varkw:

                # adds parameters from query parameters
                if request.method == 'GET':
                    data = request.values.to_dict(False)
                    kwargs = as_typed_kwargs(func, dict(**kwargs, **as_fun_params(data)))

                # Adds parameters from body parameter
                elif request.method in ['POST', 'PUT']:
                    try:
                        if request.is_json:
                            data = request.get_data()
                            if not data:
                                kwargs[varkw] = {}
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
                        current_app.logger.error(traceback.print_exc())
                        current_app.logger.debug(e)
                        raise BadRequest(str(e))

                else:
                    err_msg = f"Keyword arguments are not permitted for {request.method} method."
                    raise BadRequestKeyError(err_msg)

            else:
                if not args:
                    if request.content_length:
                        err_msg = f"TypeError: got an unexpected arguments (body: {request.json})"
                        raise BadRequestKeyError(err_msg)
                    if request.query_string:
                        err_msg = f"TypeError: got an unexpected arguments (query: {request.query_string})"
                        raise BadRequestKeyError(err_msg)
                kwargs = as_typed_kwargs(func, kwargs)

            resp = func(scaffold, **kwargs)
            if resp is None:
                return "", 204

            # Set a specific content type if response is not a tuple and entry has a default content type
            content_type = None
            if type(resp) is not tuple:
                cws_content_type = getattr(func, '__CWS_CONTENT_TYPE')
                if cws_content_type:
                    content_type = cws_content_type

            # Creates response class object
            resp = make_response(resp)

            # Forces default entry content type
            if content_type:
                resp.headers['Content-Type'] = content_type

            return resp
        except TypeError as e:
            current_app.logger.error(f"Bad request error: {str(e)}")
            raise BadRequest(str(e))
        except HTTPException as e:
            return e.description, e.code
        except Exception as e:
            current_app.logger.error(e)
            raise

    return update_wrapper(proxy, func)


def import_attr(module, attr: str, cwd='.'):
    if type(attr) is not str:
        raise AttributeError(f"{attr} is not a string.")
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
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


def check_success(resp):
    def is_success(code):
        return 200 <= code < 300

    # the body must not be None
    if resp is None:
        return False

    # unpack tuple returns
    if isinstance(resp, tuple):
        len_rv = len(resp)

        # a 3-tuple is unpacked directly
        if len_rv == 3:
            return is_success(resp[1])
        # decide if a 2-tuple has status or headers
        if len_rv == 2:
            if not isinstance(resp[1], (Headers, dict, tuple, list)):
                return is_success(resp[1])
            return True
        # other sized tuples are not allowed
        return False

    # make sure the body is an instance of the response class
    if isinstance(resp, CoworksResponse):
        return is_success(resp.status_code)

    return True


def as_typed_kwargs(func, kwargs):
    typed_kwargs = {**kwargs}
    try:
        hints = t.get_type_hints(func)
        for name, value in kwargs.items():
            hints_type = hints.get(name)
            try:
                typed_kwargs[name] = hints_type(value)
            except TypeError:
                pass
    except TypeError:
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
