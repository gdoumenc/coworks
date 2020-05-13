import requests
import pytest

from test.blueprint import *
from .tech_ms import *


class CorsMS(TechMicroService):

    def __init__(self, **kwargs):
        super().__init__(cors=True, **kwargs)

    def get(self):
        """Root access."""
        return "get"


def test_authorize_all(local_server_factory):
    ms = CorsMS()
    local_server = local_server_factory(ms)
    response = local_server.make_call(requests.options, '/', timeout=500)
    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == '*'
