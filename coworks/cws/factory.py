import os

from chalice.cli import CLIFactory
from chalice.config import Config
from chalice.constants import DEFAULT_APIGATEWAY_STAGE_NAME, DEFAULT_ENDPOINT_TYPE


class CwsFactory(CLIFactory):
    def __init__(self, app, project_dir, **kwargs):
        self.app = app
        super().__init__(project_dir, **kwargs)

    def load_chalice_app(self, environment_variables=None, **kwargs):
        if environment_variables is not None:
            self._environ.update(environment_variables)
            for key, val in self._environ.items():
                os.environ[key] = val
        return self.app

    def create_config_obj(self, chalice_stage_name='DEFAULT_STAGE_NAME',
                          autogen_policy=None,
                          api_gateway_stage=None):
        default_params = {
            'project_dir': self.project_dir,
            'api_gateway_stage': DEFAULT_APIGATEWAY_STAGE_NAME,
            'api_gateway_endpoint_type': DEFAULT_ENDPOINT_TYPE,
            'autogen_policy': False
        }
        config_from_disk = {
            'version': 1,
            'name': 'app',
            'stages': {
            }
        }
        config = Config(user_provided_params={},
                        config_from_disk=config_from_disk,
                        default_params=default_params)

        config._chalice_app = self.app
        return config
