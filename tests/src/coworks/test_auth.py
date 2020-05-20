import requests
from chalice import AuthResponse

from .tech_ms import SimpleMS
from .blueprint.blueprint import BP


class AuthorizeAllMS(SimpleMS):

    def __init__(self):
        super().__init__()
        self.register_blueprint(BP(), url_prefix="/blueprint")

    def auth(self, auth_request):
        return True


class AuthorizeNothingMS(SimpleMS):

    def __init__(self):
        super().__init__()
        self.register_blueprint(BP(), url_prefix="/blueprint")

    def auth(self, auth_request):
        return False


class AuthorizedMS(SimpleMS):

    def auth(self, auth_request):
        token = auth_request.token
        if token == 'allow':
            return AuthResponse(routes=['/'], principal_id='user')
        return False


def test_authorize_all(local_server_factory):
    local_server = local_server_factory(AuthorizeAllMS())
    response = local_server.make_call(requests.get, '/', headers={'authorization': 'token'})
    assert response.status_code == 200
    assert response.text == 'get'
    response = local_server.make_call(requests.get, '/blueprint/test/3', headers={'authorization': 'token'})
    assert response.status_code == 200
    assert response.text == 'blueprint test 3'


def test_authorize_nothing(local_server_factory):
    local_server = local_server_factory(AuthorizeNothingMS())
    response = local_server.make_call(requests.get, '/', headers={'authorization': 'token'})
    assert response.status_code == 403
    response = local_server.make_call(requests.get, '/blueprint/test/3', headers={'authorization': 'token'})
    assert response.status_code == 403


def test_authorized(local_server_factory):
    local_server = local_server_factory(AuthorizedMS())
    response = local_server.make_call(requests.get, '/', headers={'authorization': 'allow'})
    assert response.status_code == 200
    assert response.text == 'get'
    response = local_server.make_call(requests.get, '/', headers={'authorization': 'refuse'})
    assert response.status_code == 403
