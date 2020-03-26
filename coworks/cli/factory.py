import importlib
import os

import sys

from chalice.cli import CLIFactory
from ..export import Writer


class CWSFactory(CLIFactory):
    def __init__(self, app, project_dir, **kwargs):
        self.app = app
        super().__init__(project_dir, **kwargs)

    @staticmethod
    def import_attr(module, attr, project_dir='.'):
        if project_dir not in sys.path:
            sys.path.insert(0, project_dir)
        app_module = importlib.import_module(module)
        return getattr(app_module, attr)

    def load_chalice_app(self, environment_variables=None, **kwargs):
        if environment_variables is not None:
            self._environ.update(environment_variables)
            for key, val in self._environ.items():
                os.environ[key] = val
        return self.app

    def run_local_server(self, config, host, port):
        app_obj = config.chalice_app
        server = super().create_local_server(app_obj, config, host, port)
        server.serve_forever()

    def create_default_deployer(self, session, config, ui):
        return super().create_default_deployer(session, config, ui)

    def create_botocore_session(self, **kwargs):
        return None
