import importlib
import os
import sys

from chalice.cli import CLIFactory
from chalice.config import Config
from chalice.constants import DEFAULT_APIGATEWAY_STAGE_NAME, DEFAULT_ENDPOINT_TYPE


class CwsCLIFactory(CLIFactory):
    def __init__(self, app, project_dir, **kwargs):
        self.app = app
        super().__init__(project_dir, **kwargs)

    @staticmethod
    def import_attr(module, attr, cwd='.'):
        if cwd not in sys.path:
            sys.path.insert(0, cwd)
        app_module= importlib.import_module(module)
        if "PYTEST_CURRENT_TEST" in os.environ:
            # needed as Chalice local server change class
            app_module = importlib.reload(app_module)
        return getattr(app_module, attr)

    def load_chalice_app(self, environment_variables=None, **kwargs):
        if environment_variables is not None:
            self._environ.update(environment_variables)
            for key, val in self._environ.items():
                os.environ[key] = val
        return self.app

    def run_local_server(self, app, config, host, port):
        app_obj = config.chalice_app
        app.local_server = self.create_local_server(app_obj, config, host, port)
        app.local_server.serve_forever()

    def mock_config_obj(self, app, chalice_stage_name):
        default_params = {
            'project_dir': self.project_dir,
            'api_gateway_stage': DEFAULT_APIGATEWAY_STAGE_NAME,
            'api_gateway_endpoint_type': DEFAULT_ENDPOINT_TYPE,
            'autogen_policy': False
        }
        config_from_disk = {
            'version': 1,
            'app_name': 'app',
            'stages': {
                chalice_stage_name: {
                    'api_gateway_stage': 'test',
                }
            }
        }
        config = Config(chalice_stage=chalice_stage_name,
                        user_provided_params={},
                        config_from_disk=config_from_disk,
                        default_params=default_params)

        config._chalice_app = app
        return config
