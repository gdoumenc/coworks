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
        config = Config(environment_variables_file=Path(EXAMPLE_DIR) / "_dev_vars.json")
        local_server = local_server_factory(WithEnvMS(config=config))
        response = local_server.make_call(requests.get, '/')
        assert response.status_code == 200
        assert response.text == 'test environment variable'

    def test_prod_stage(self, local_server_factory):
        config = Config(environment_variables_file=Path(EXAMPLE_DIR) / "_prod_vars.json")
        local_server = local_server_factory(WithEnvMS(config=config))
        response = local_server.make_call(requests.get, '/')
        assert response.status_code == 200
        assert response.text == 'prod variable'
