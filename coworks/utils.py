import inspect
import logging
import sys
import os


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


def run_app_server(self, host='127.0.0.1', port=8000, stage=None, profile=None):
    """Method defined to be used in IDE for debug.
    As chalice.cli is not deployed in AWS must iport only when used."""
    from chalice.cli import CLIFactory, run_local_server
    from chalice.cli import DEFAULT_STAGE_NAME
    stage = stage or DEFAULT_STAGE_NAME

    class CWSFactory(CLIFactory):
        def __init__(self, app, project_dir):
            self.app = app
            super().__init__(project_dir, debug=True, profile=profile)

        def load_chalice_app(self, environment_variables=None, **kwargs):
            if environment_variables is not None:
                self._environ.update(environment_variables)
                for key, val in self._environ.items():
                    os.environ[key] = val
            return self.app

    factory = CWSFactory(self, '.')
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')
    run_local_server(factory, host, port, stage)
