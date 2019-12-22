import inspect


def class_rest_methods(obj):
    """Returns the list of methods from the class."""
    methods = inspect.getmembers(obj.__class__, lambda x: inspect.isfunction(x))

    res = []
    for name, func in methods:
        if name == 'get' or name.startswith('get_'):
            res.append(('get', func))
        elif name.startswith('post'):
            res.append(('post', func))
        elif name.startswith('put'):
            res.append(('put', func))
        elif name.startswith('delete'):
            res.append(('delete', func))
        elif name.startswith('patch'):
            res.append(('patch', func))
    return res


def class_attribute(obj, name: str = None, defaut=None):
    """Returns the list of attributes from the class or the attribute if name parameter is defined
    or default value if not found."""
    attributes = inspect.getmembers(obj.__class__, lambda x: not inspect.isroutine(x))

    if not name:
        return attributes

    filtered = [a[1] for a in attributes if a[0] == name]
    return filtered[0] if filtered else defaut
