import importlib
import inspect
import json
import os
import platform
import sys

HTTP_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS']


def jsonify(result, pretty=False, indent=None, separators=None):
    if pretty:
        indent = indent or 4
        separators = separators or (",", ": ")
    else:
        separators = separators or (",", ":")

    return json.dumps(result, indent=indent, separators=separators)


def import_attr(module, attr, cwd='.'):
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
            return func
    return None


def class_cws_methods(obj):
    """Returns the list of methods from the class."""
    methods = inspect.getmembers(obj.__class__, lambda x: inspect.isfunction(x))

    return [fun for _, fun in methods if hasattr(fun, '__CWS_METHOD')]


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
    Trailing but not leading slashes are stripped for each argument.
    """

    reduced = [x.lstrip('/').rstrip('/') for x in args if x]
    return '/'.join([x for x in reduced if x])


def make_absolute(route):
    return '/' + path_join(route)


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
    python_info = f"python {sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}"
    platform_system = platform.system().lower()
    platform_release = platform.release()
    platform_info = f"{platform_system} {platform_release}"
    return f"{python_info}, {platform_info}"
