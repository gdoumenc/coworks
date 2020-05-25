import inspect

from aws_xray_sdk.core import xray_recorder


def class_auth_methods(obj):
    """Returns the auth method from the class if exists."""
    methods = inspect.getmembers(obj.__class__, lambda x: inspect.isfunction(x))

    for name, func in methods:
        if name == 'auth':
            return func
    return None


def class_rest_methods(obj):
    """Returns the list of methods from the class."""
    methods = inspect.getmembers(obj.__class__, lambda x: inspect.isfunction(x))

    res = []
    for name, func in methods:
        if name == 'get' or name.startswith('get_'):
            res.append(('get', func))
        elif name == 'post' or name.startswith('post_'):
            res.append(('post', func))
        elif name == 'put' or name.startswith('put_'):
            res.append(('put', func))
        elif name == 'delete' or name.startswith('delete_'):
            res.append(('delete', func))
        elif name == 'patch' or name.startswith('patch_'):
            res.append(('patch', func))
        elif name == 'options' or name.startswith('options_'):
            res.append(('options', func))
    return res


def class_attribute(obj, name: str = None, defaut=None):
    """Returns the list of attributes from the class or the attribute if name parameter is defined
    or default value if not found."""
    attributes = inspect.getmembers(obj.__class__, lambda x: not inspect.isroutine(x))

    if not name:
        return attributes

    filtered = [a[1] for a in attributes if a[0] == name]
    return filtered[0] if filtered else defaut


def trim_underscores(name):
    while name.startswith('_'):
        name = name[1:]
    while name.endswith('_'):
        name = name[:-1]
    return name


def begin_xray_subsegment(subsegment_name):
    if xray_recorder.in_segment().segment is not None:
        return xray_recorder.begin_subsegment(subsegment_name)
    return None


def end_xray_subsegment():
    if xray_recorder.in_subsegment().subsegment is not None:
        return xray_recorder.end_subsegment()
