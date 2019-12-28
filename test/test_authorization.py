import requests

from .microservice import *


def test_authorize_all(local_server_factory):
    local_server = local_server_factory(AuthorizeAllMS())
    response = local_server.make_call(requests.get, '/', headers={'authorization': 'token'})
    assert response.status_code == 200
    assert response.text == 'get'


def test_authorize_nothing(local_server_factory):
    local_server = local_server_factory(AuthorizeNothingMS())
    response = local_server.make_call(requests.get, '/', headers={'authorization': 'token'})
    assert response.status_code == 403


def test_authorized(local_server_factory):
    local_server = local_server_factory(AuthorizedMS())
    response = local_server.make_call(requests.get, '/', headers={'authorization': 'allow'})
    assert response.status_code == 200
    assert response.text == 'get'
    response = local_server.make_call(requests.get, '/', headers={'authorization': 'refuse'})
    assert response.status_code == 403
