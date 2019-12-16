import contextlib
import pytest
import requests
import socket
from threading import Thread, Event

from chalice.local import LocalDevServer
from chalice.config import Config

from .microservice import *


class ThreadedLocalServer(Thread):
    def __init__(self, port, host='localhost'):
        super(ThreadedLocalServer, self).__init__()
        self._app_object = None
        self._config = None
        self._host = host
        self._port = port
        self._server = None
        self._server_ready = Event()

    def wait_for_server_ready(self):
        self._server_ready.wait()

    def configure(self, app_object, config):
        self._app_object = app_object
        self._config = config

    def run(self):
        self._server = LocalDevServer(
            self._app_object, self._config, self._host, self._port)
        self._server_ready.set()
        self._server.serve_forever()

    def make_call(self, method, path, port, timeout=0.5, **kwarg):
        self._server_ready.wait()
        return method('http://{host}:{port}{path}'.format(
            path=path, host=self._host, port=port), timeout=timeout, **kwarg)

    def shutdown(self):
        if self._server is not None:
            self._server.server.shutdown()


@pytest.fixture()
def unused_tcp_port():
    with contextlib.closing(socket.socket()) as sock:
        sock.bind(('localhost', 0))
        return sock.getsockname()[1]


@pytest.fixture()
def local_server_factory(unused_tcp_port):
    threaded_server = ThreadedLocalServer(unused_tcp_port)

    def create_server(app_object):
        threaded_server.configure(app_object, Config())
        threaded_server.start()
        return threaded_server, unused_tcp_port

    try:
        yield create_server
    finally:
        threaded_server.shutdown()


def test_request(local_server_factory):
    local_server, port = local_server_factory(MS())
    response = local_server.make_call(requests.get, '/', port)
    assert response.status_code == 200
    assert response.text == 'get'
    response = local_server.make_call(requests.get, '/get1', port)
    assert response.status_code == 403
    response = local_server.make_call(requests.get, '/content', port)
    assert response.status_code == 200
    assert response.text == 'get_content'
    response = local_server.make_call(requests.post, '/', port)
    assert response.status_code == 405


def test_slug_redefined(local_server_factory):
    local_server, port = local_server_factory(SlugMS())
    response = local_server.make_call(requests.get, '/slug', port)
    assert response.status_code == 200
    assert response.text == "hello world"


def test_parameterized(local_server_factory):
    local_server, port = local_server_factory(ParamMS())
    response = local_server.make_call(requests.get, '/123', port)
    assert response.status_code == 200
    assert response.text == '123'
    response = local_server.make_call(requests.get, '/concat/123/456', port)
    assert response.status_code == 200
    assert response.text == '123456'
    response = local_server.make_call(requests.get, '/value', port)
    assert response.status_code == 200
    assert response.text == '123'
    response = local_server.make_call(requests.put, '/value', port, json={'value': "456"})
    assert response.status_code == 200
    assert response.text == '456'
    response = local_server.make_call(requests.get, '/value', port)
    assert response.status_code == 200
    assert response.text == '456'


def test_slug_parameterized(local_server_factory):
    local_server, port = local_server_factory(SlugParamMS())
    response = local_server.make_call(requests.get, '/slug/123', port)
    assert response.status_code == 200
    assert response.text == '123'
    response = local_server.make_call(requests.get, '/slug/concat/123/456', port)
    assert response.status_code == 200
    assert response.text == '123456'
