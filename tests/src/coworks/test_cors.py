import requests

from coworks import Config, CORSConfig
from .tech_ms import *


class AllCorsMS(TechMicroService):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self):
        """Root access."""
        return "get"


def test_authorize_all(local_server_factory):
    ms = AllCorsMS()
    local_server = local_server_factory(ms)
    response = local_server.make_call(requests.options, '/', timeout=500)
    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == '*'


class OneCorsMS(TechMicroService):

    def __init__(self, **kwargs):
        config = Config(cors=CORSConfig(allow_origin='www.test.fr'))
        super().__init__(config=config, **kwargs)

    def get(self):
        """Root access."""
        return "get"


def test_authorize_one(local_server_factory):
    ms = OneCorsMS()
    local_server = local_server_factory(ms)
    response = local_server.make_call(requests.options, '/', timeout=500)
    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == 'www.test.fr'
