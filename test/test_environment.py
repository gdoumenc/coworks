import requests
import os

from .tech_ms import *


class WithEnvMS(SimpleMS):

    def get(self):
        """Root access."""
        return os.getenv("test")


def test_default(local_server_factory):
    local_server = local_server_factory(WithEnvMS(), config_path="test/example")
    response = local_server.make_call(requests.get, '/')
    assert response.status_code == 200
    assert response.text == 'test environment variable'


def test_dev_stage(local_server_factory):
    local_server = local_server_factory(WithEnvMS(), config_path="test/example", stage="dev")
    response = local_server.make_call(requests.get, '/')
    assert response.status_code == 200
    assert response.text == 'test environment variable'


def test_prod_stage(local_server_factory):
    local_server = local_server_factory(WithEnvMS(), config_path="test/example", stage="master")
    response = local_server.make_call(requests.get, '/')
    assert response.status_code == 200
    assert response.text == 'prod variable'
