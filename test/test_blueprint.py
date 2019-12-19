import pytest
import requests

from .local_server import ThreadedLocalServer
from .microservice import *
from .blueprint import *


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


def test_request(local_server_factory):
    ms = SimpleMS()
    ms.register_blueprint(BP("blueprint"))
    local_server = local_server_factory(ms)
    response = local_server.make_call(requests.get, '/')
    assert response.status_code == 200
    assert response.text == 'get'
    response = local_server.make_call(requests.get, '/blueprint')
    assert response.status_code == 200
    assert response.text == 'blueprint root'
    response = local_server.make_call(requests.get, '/blueprint/test/3')
    assert response.status_code == 200
    assert response.text == 'blueprint test 3'
