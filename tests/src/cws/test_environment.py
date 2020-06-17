import os
from pathlib import Path

import requests

from coworks.config import Config
from tests.src.coworks.tech_ms import *

EXAMPLE_DIR = os.getenv('EXAMPLE_DIR')


class WithEnvMS(SimpleMS):

    def get(self):
        """Root access."""
        return os.getenv("test")


class TestClass:

    def test_dev_stage(self, local_server_factory):
        config = Config(environment_variables_file=Path(EXAMPLE_DIR) / "config" / "vars_dev.json")
        local_server = local_server_factory(WithEnvMS(configs=config))
        response = local_server.make_call(requests.get, '/')
        assert response.status_code == 200
        assert response.text == 'test dev environment variable'

    def test_prod_stage(self, local_server_factory):
        config = Config(environment_variables_file=Path(EXAMPLE_DIR) / "config" / "vars_prod.secret.json")
        local_server = local_server_factory(WithEnvMS(configs=config))
        response = local_server.make_call(requests.get, '/')
        assert response.status_code == 200
        assert response.text == 'test prod environment variable'
