from functools import update_wrapper, partial
import inspect
import logging
import sys
import os

from chalice import Chalice

from .utils import class_rest_methods, class_attribute


class TechMicroService(Chalice):

    def __init__(self, *args, **kwargs):
        # TODO Positional only argument when python 3.8 will be available on Lambda
        super().__init__(*args, **kwargs)
        self.experimental_feature_flags.update([
            'BLUEPRINTS'
        ])

        # add root route
        slug = class_attribute(self, 'slug', '')
        methods = class_rest_methods(self)
        for method, func in methods:
            if func.__name__ == method:
                route = f"{slug}"
            else:
                name = func.__name__[4:]
                route = f"{slug}/{name}" if slug else f"{name}"
            args = inspect.getfullargspec(func).args[1:]
            for arg in args:
                route = route + f"/{{{arg}}}" if route else f"{{{arg}}}"

            proxy = update_wrapper(partial(func, self), func)
            self.route(f"/{route}", methods=[method.upper()])(proxy)

    def run(self, host='127.0.0.1', port=8000, stage=None, debug=True, profile=None):
        from chalice.cli import CLIFactory, chalice_version, get_system_info, run_local_server, create_local_server, \
            reloader
        from chalice.cli import CONFIG_VERSION, DEFAULT_STAGE_NAME, DEFAULT_APIGATEWAY_STAGE_NAME
        # DEFAULT_STAGE_NAME

        class CWSFactory(CLIFactory):
            def __init__(self, app, project_dir, debug=False, profile=None, environ=None):
                self.app = app
                super().__init__(project_dir, debug=debug, profile=profile, environ=environ)

            def load_chalice_app(self, environment_variables=None, **kwargs):
                if environment_variables is not None:
                    self._environ.update(environment_variables)
                    for key, val in self._environ.items():
                        os.environ[key] = val
                return self.app

        factory = CWSFactory(self, '.', debug=debug, profile=profile)
        logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')
        run_local_server(factory, host, port, stage)
