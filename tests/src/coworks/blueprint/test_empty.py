import requests

from coworks import Blueprint, entry
from tests.src.coworks.tech_ms import TechMS


class BP(Blueprint):

    @entry
    def get(self):
        return f"blueprint test"


class TestClass:
    def test_request(self, local_server_factory):
        ms = TechMS()
        ms.register_blueprint(BP())
        local_server = local_server_factory(ms)
        response = local_server.make_call(requests.get, '/', timeout=500)
        assert response.status_code == 200
        assert response.text == 'blueprint test'
