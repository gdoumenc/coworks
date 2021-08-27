import importlib
import inspect
import os
import platform
import sys

from aws_xray_sdk.core.exceptions.exceptions import SegmentNotFoundException
from flask import Response
from flask import request
from flask.blueprints import BlueprintSetupState
from functools import partial

HTTP_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS']


def init_routes(app, bp_state: BlueprintSetupState = None, hide_routes: bool = False) -> None:
    """ Creates all routes for a microservice.
    :param app the app microservice
    :param bp_state the blueprint state
    :param hide_routes list of routes to be hidden.
    """

    # Adds entrypoints
    obj = bp_state.blueprint if bp_state else app
    method_members = inspect.getmembers(obj.__class__, lambda x: inspect.isfunction(x))
    methods = [fun for _, fun in method_members if hasattr(fun, '__CWS_METHOD')]
    for fun in methods:
        if hide_routes is True or getattr(fun, '__CWS_HIDDEN', False):
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

        proxy = _create_rest_proxy(app, fun, kwarg_keys, args, varkw)

        # Creates the entry
        if hide_routes is False or (type(hide_routes) is list and entry_path not in hide_routes):
            url_prefix = bp_state.url_prefix if bp_state else ''
            rule = make_absolute(entry_path, url_prefix)
            app.add_url_rule(rule=rule, view_func=proxy, methods=[method])
            # authorizer=auth,
            # cors=self.current_app.config.cors,
            # content_types=list(self.current_app.config.content_type)


def _create_rest_proxy(app, func, kwarg_keys, args, varkw):
    import traceback

    import urllib
    from aws_xray_sdk.core import xray_recorder
    from functools import update_wrapper, partial
    from requests_toolbelt.multipart import MultipartDecoder

    original_app_class = app.__class__

    def proxy(**kwargs):
        try:
            # Adds kwargs parameters
            def check_param_expected_in_lambda(param_name):
                """Alerts when more parameters than expected are defined in request."""
                if param_name not in kwarg_keys and varkw is None:
                    err_msg = f"TypeError: got an unexpected keyword argument '{param_name}'"
                    return Response(err_msg, 400)

            def add_param(param_name, param_value):
                check_param_expected_in_lambda(param_name)
                if param_name in params:
                    if isinstance(params[param_name], list):
                        params[param_name].append(param_value)
                    else:
                        params[param_name] = [params[param_name], param_value]
                else:
                    params[param_name] = param_value

            # get keyword arguments from request
            if kwarg_keys or varkw:
                params = {}

                # adds parameters from query parameters
                if request.method == 'GET':
                    for k in request.values or {}:
                        v = request.values.getlist(k)
                        add_param(k, v if len(v) > 1 else v[0])
                    kwargs = dict(**kwargs, **params)

                # adds parameters from body parameter
                elif request.method in ['POST', 'PUT']:
                    try:
                        content_type = request.headers.get('content-type', 'application/json')
                        if content_type.startswith('multipart/form-data'):
                            try:
                                multipart_decoder = MultipartDecoder(request.raw_body, content_type)
                                for part in multipart_decoder.parts:
                                    name, content = get_multipart_content(part)
                                    add_param(name, content)
                            except Exception as e:
                                return Response(str(e), 400)
                            kwargs = dict(**kwargs, **params)
                        elif content_type.startswith('application/x-www-form-urlencoded'):
                            params = urllib.parse.parse_qs(request.raw_body.decode("utf-8"))
                            kwargs = dict(**kwargs, **params)
                        elif content_type.startswith('application/json'):
                            if hasattr(request.json, 'items'):
                                params = {}
                                for k, v in request.json.items():
                                    add_param(k, v)
                                kwargs = dict(**kwargs, **params)
                            # else:
                            #     kwargs[kwarg_keys[0]] = request.json
                        elif content_type.startswith('text/plain'):
                            kwargs[kwarg_keys[0]] = request.json
                        else:
                            err = f"Cannot manage content type {content_type} for {app}"
                            return Response(err, 400)
                    except Exception as e:
                        app.logger.error(traceback.print_exc())
                        app.logger.debug(e)
                        return Response(str(e), 400)

                else:
                    err = f"Keyword arguments are not permitted for {request.method} method."
                    return Response(err, 400)

            else:
                if not args:
                    if request.content_length is not None:
                        err = f"TypeError: got an unexpected arguments (body: {request.json})"
                        return Response(err, 400)
                    if request.query_string:
                        err = f"TypeError: got an unexpected arguments (query: {request.query_string})"
                        return Response(err, 400)

            # # chalice is changing class for local server for threading reason (why not mixin..?)
            # self_class = self.__class__
            # if self_class != original_app_class:
            #     self.__class__ = original_app_class

            resp = func(app, **kwargs)
            # self.__class__ = self_class
            return resp
        except TypeError as e:
            return Response(str(e), 400)
        except Exception as e:
            try:
                subsegment = xray_recorder.current_subsegment()
                if subsegment:
                    subsegment.add_error_flag()
            except SegmentNotFoundException:
                pass
            raise

    proxy = update_wrapper(proxy, func)
    proxy.__cws_func__ = update_wrapper(partial(func, app), func)
    return proxy


def import_attr(module, attr: str, cwd='.'):
    if type(attr) is not str:
        raise AttributeError(f"{attr} is not a string.")
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    app_module = importlib.import_module(module)
    if "PYTEST_CURRENT_TEST" in os.environ:
        # needed as Chalice local server change class
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
    if not route.startswith('/'):
        route = '/' + route
    if url_prefix:
        route = '/' + url_prefix.lstrip('/').rstrip('/') + route
    return route


def trim_underscores(name):
    while name.startswith('_'):
        name = name[1:]
    while name.endswith('_'):
        name = name[:-1]
    return name


def as_list(var):
    if var is None:
        return []
    if type(var) is list:
        return var
    return [var]


def get_system_info():
    from flask import __version__ as flask_version

    flask_info = f"flask {flask_version}"
    python_info = f"python {sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}"
    platform_system = platform.system().lower()
    platform_release = platform.release()
    platform_info = f"{platform_system} {platform_release}"
    return f"{flask_info}, {python_info}, {platform_info}"


class FileParam:

    def __init__(self, file, mime_type):
        self.file = file
        self.mime_type = mime_type

    def __repr__(self):
        if self.mime_type:
            return f'FileParam({self.file.name}, {self.mime_type})'
        return f'FileParam({self.file.name})'
