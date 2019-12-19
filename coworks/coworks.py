from functools import update_wrapper, partial
import inspect
import logging
import sys
import os

from chalice import Chalice, Blueprint as ChaliceBlueprint

from .utils import class_rest_methods, class_attribute


class TechMicroService(Chalice):

    def __init__(self, *args, **kwargs):
        # TODO Positional only argument when python 3.8 will be available on Lambda
        super().__init__(*args, **kwargs)
        self.experimental_feature_flags.update([
            'BLUEPRINTS'
        ])

        # add root route
        self._add_route()

    def register_blueprint(self, blueprint, **kwargs):
        slug = class_attribute(blueprint, 'slug', '')
        self._add_route(blueprint)
        if 'name_prefix' not in kwargs:
            kwargs['name_prefix'] = blueprint.import_name
        if not slug and 'url_prefix' not in kwargs:
            kwargs['url_prefix'] = f"/{blueprint.import_name}"
        super().register_blueprint(blueprint, **kwargs)

    def run(self, host='127.0.0.1', port=8000, stage=None, debug=True, profile=None):
        # TODO missing test
        from chalice.cli import CLIFactory, run_local_server
        from chalice.cli import DEFAULT_STAGE_NAME
        stage = stage or DEFAULT_STAGE_NAME

        class CWSFactory(CLIFactory):
            def __init__(self, app, project_dir, environ=None):
                self.app = app
                super().__init__(project_dir, debug=debug, profile=profile, environ=environ)

            def load_chalice_app(self, environment_variables=None, **kwargs):
                if environment_variables is not None:
                    self._environ.update(environment_variables)
                    for key, val in self._environ.items():
                        os.environ[key] = val
                return self.app

        factory = CWSFactory(self, '.')
        logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')
        run_local_server(factory, host, port, stage)

    def _add_route(self, component=None):
        component = component if component else self
        slug = class_attribute(component, 'slug', '')
        methods = class_rest_methods(component)
        for method, func in methods:
            if func.__name__ == method:
                route = f"{slug}"
            else:
                name = func.__name__[4:]
                route = f"{slug}/{name}" if slug else f"{name}"
            args = inspect.getfullargspec(func).args[1:]
            for arg in args:
                route = route + f"/{{{arg}}}" if route else f"{{{arg}}}"

            proxy = update_wrapper(partial(func, component), func)
            component.route(f"/{route}", methods=[method.upper()])(proxy)


class Blueprint(ChaliceBlueprint):

    @property
    def import_name(self):
        return self._import_name
