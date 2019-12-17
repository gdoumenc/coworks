import contextlib
import pytest
import requests
import socket

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


def test_slug_redefined(local_server_factory):
    local_server = local_server_factory(SlugMS())
    response = local_server.make_call(requests.get, '/slug')
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
    local_server = local_server_factory(SlugParamMS())
    response = local_server.make_call(requests.get, '/slug/123')
    assert response.status_code == 200
    assert response.text == '123'
    response = local_server.make_call(requests.get, '/slug/concat/123/456')
    assert response.status_code == 200
    assert response.text == '123456'
