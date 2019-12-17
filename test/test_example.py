import pytest
import requests

from collections import defaultdict

from coworks import TechMicroService

from .local_server import ThreadedLocalServer


@pytest.fixture()
def local_server_factory():
    threaded_server = ThreadedLocalServer()

    def create_server(app):
        threaded_server.configure(app)
        threaded_server.start()
        return threaded_server

    try:
        yield create_server
    finally:
        threaded_server.shutdown()


class SimpleExampleMicroservice(TechMicroService):
    values = defaultdict(int)

    def get(self):
        return "Simple microservice for test."

    def get_value(self, index):
        return self.values[index]

    def put_value(self, index):
        request = self.current_request
        self.values[index] = request.json_body
        return self.values[index]


def test_simple_example(local_server_factory):
    local_server = local_server_factory(SimpleExampleMicroservice("example"))
    response = local_server.make_call(requests.get, '/')
    assert response.status_code == 200
    assert response.text == "Simple microservice for test."
    response = local_server.make_call(requests.get, '/value/1')
    assert response.status_code == 200
    assert response.text == "0"
    response = local_server.make_call(requests.put, '/value/1', json=1)
    assert response.status_code == 200
    assert response.text == "1"
    response = local_server.make_call(requests.get, '/value/1')
    assert response.status_code == 200
    assert response.text == "1"
