import pytest
import requests

from .local_server import ThreadedLocalServer
from .microservice import *


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
    local_server = local_server_factory(SimpleMS())
    response = local_server.make_call(requests.get, '/')
    assert response.status_code == 200
    assert response.text == 'get'
    response = local_server.make_call(requests.get, '/get1')
    assert response.status_code == 403
    response = local_server.make_call(requests.get, '/content')
    assert response.status_code == 200
    assert response.text == 'get_content'
    response = local_server.make_call(requests.post, '/')
    assert response.status_code == 405
    response = local_server.make_call(requests.post, '/content/3')
    assert response.status_code == 200
    assert response.text == 'post_content 3'
    response = local_server.make_call(requests.get, '/extended/content')
    assert response.status_code == 200
    assert response.text == 'hello world'


def test_prefixed(local_server_factory):
    local_server = local_server_factory(PrefixedMS())
    response = local_server.make_call(requests.get, '/prefix')
    assert response.status_code == 200
    assert response.text == "hello world"
    response = local_server.make_call(requests.get, '/prefix/content')
    assert response.status_code == 200
    assert response.text == "hello world"
    response = local_server.make_call(requests.get, '/prefix/extended/content')
    assert response.status_code == 200
    assert response.text == "hello world"


def test_parameterized(local_server_factory):
    local_server = local_server_factory(ParamMS())
    response = local_server.make_call(requests.get, '/123')
    assert response.status_code == 200
    assert response.text == '123'
    response = local_server.make_call(requests.get, '/concat/123/456')
    assert response.status_code == 200
    assert response.text == '123456'
    response = local_server.make_call(requests.get, '/value')
    assert response.status_code == 200
    assert response.text == '123'
    response = local_server.make_call(requests.put, '/value', json={'value': "456"})
    assert response.status_code == 200
    assert response.text == '456'
    response = local_server.make_call(requests.get, '/value')
    assert response.status_code == 200
    assert response.text == '456'


def test_slug_parameterized(local_server_factory):
    local_server = local_server_factory(PrefixedParamMS())
    response = local_server.make_call(requests.get, '/prefix/123')
    assert response.status_code == 200
    assert response.text == '123'
    response = local_server.make_call(requests.get, '/prefix/concat/123/456')
    assert response.status_code == 200
    assert response.text == '123456'
