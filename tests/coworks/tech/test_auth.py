import requests

from coworks import entry
from coworks.config import Config
from tests.coworks.blueprint.blueprint import BP
from tests.coworks.ms import SimpleMS


class AuthorizeAll(SimpleMS):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_blueprint(BP(), url_prefix="/blueprint")

    def auth(self, auth_request):
        return True

    @entry
    def get_product(self, ref):
        return ref


class AuthorizeNothingExceptBP(SimpleMS):

    def __init__(self):
        super().__init__()
        self.register_blueprint(BP(), url_prefix="/blueprint")

    def auth(self, auth_request):
        return ['/blueprint/*']


class AuthorizeNothing(SimpleMS):

    def __init__(self):
        super().__init__()
        self.register_blueprint(BP(), url_prefix="/blueprint")

    def auth(self, auth_request):
        return False


class AuthorizedMS(SimpleMS):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_blueprint(BP(), url_prefix="/blueprint")

    def auth(self, auth_request):
        if auth_request.token == 'allow':
            return AuthResponse(routes=['*'], principal_id='user')
        return False


class AuthorizedOnlyRootMS(SimpleMS):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_blueprint(BP(), url_prefix="/blueprint")

    def auth(self, auth_request):
        if auth_request.token == 'allow':
            return ['/']
        return False


import pytest
@pytest.mark.skip
class TestClass:
    def test_authorize_all(self, local_server_factory):
        local_server = local_server_factory(AuthorizeAll())
        response = local_server.make_call(requests.get, '/', headers={'authorization': 'token'})
        assert response.status_code == 200
        assert response.text == 'get'
        response = local_server.make_call(requests.get, '/blueprint/test/3', headers={'authorization': 'token'})
        assert response.status_code == 200
        assert response.text == 'blueprint test 3'

    def test_authorize_nothing_except_bp(self, local_server_factory):
        local_server = local_server_factory(AuthorizeNothingExceptBP())
        response = local_server.make_call(requests.get, '/', headers={'authorization': 'allow'})
        assert response.status_code == 403
        response = local_server.make_call(requests.get, '/blueprint/test/3', headers={'authorization': 'allow'})
        assert response.status_code == 200

    def test_authorize_nothing(self, local_server_factory):
        local_server = local_server_factory(AuthorizeNothing())
        response = local_server.make_call(requests.get, '/', headers={'authorization': 'allow'})
        assert response.status_code == 403
        response = local_server.make_call(requests.get, '/blueprint/test/3', headers={'authorization': 'allow'})
        assert response.status_code == 403

    def test_authorized(self, local_server_factory):
        local_server = local_server_factory(AuthorizedMS())
        response = local_server.make_call(requests.get, '/', headers={'authorization': 'allow'})
        assert response.status_code == 200
        assert response.text == 'get'
        response = local_server.make_call(requests.get, '/', headers={'authorization': 'refuse'})
        assert response.status_code == 403
        response = local_server.make_call(requests.get, '/blueprint/test/3', headers={'authorization': 'allow'})
        assert response.status_code == 200
        assert response.text == 'blueprint test 3'
        response = local_server.make_call(requests.get, '/blueprint/test/3', headers={'authorization': 'refuse'})
        assert response.status_code == 403

    def test_authorized2(self, local_server_factory):
        local_server = local_server_factory(AuthorizedOnlyRootMS())
        response = local_server.make_call(requests.get, '/', headers={'authorization': 'allow'})
        assert response.status_code == 200
        assert response.text == 'get'
        response = local_server.make_call(requests.get, '/', headers={'authorization': 'refuse'})
        assert response.status_code == 403
        response = local_server.make_call(requests.get, '/blueprint/test/3', headers={'authorization': 'allow'})
        assert response.status_code == 403
        assert response.text == '{"Message": "User is not authorized to access this resource"}'
        response = local_server.make_call(requests.get, '/blueprint/test/3', headers={'authorization': 'refuse'})
        assert response.status_code == 403
        assert response.text == '{"Message": "User is not authorized to access this resource"}'

    def test_authorized_external(self, local_server_factory):
        config = Config(auth=auth_external)
        local_server = local_server_factory(AuthorizedMS(configs=[config]))
        response = local_server.make_call(requests.get, '/', headers={'authorization': 'allow'})
        assert response.status_code == 200
        assert response.text == 'get'
        response = local_server.make_call(requests.get, '/', headers={'authorization': 'refuse'})
        assert response.status_code == 403
        response = local_server.make_call(requests.get, '/blueprint/test/3', headers={'authorization': 'allow'})
        assert response.status_code == 200
        assert response.text == 'blueprint test 3'
        response = local_server.make_call(requests.get, '/blueprint/test/3', headers={'authorization': 'refuse'})
        assert response.status_code == 403

    def test_auth_entry(self, local_server_factory):
        ms = AuthorizedMS()
        local_server = local_server_factory(ms)
        response = local_server.make_call(requests.get, '/', headers={'authorization': 'allow'})
        assert response.status_code == 200
        assert ms._entry('/', 'GET').auth
        assert response.status_code == 200
        response = local_server.make_call(requests.get, '/blueprint/test/3', headers={'authorization': 'allow'})
        assert response.status_code == 200
        assert ms._entry('/blueprint/test/3', 'GET').auth

    def test_entries(self, local_server_factory):
        ms = AuthorizeAll()
        local_server = local_server_factory(ms)
        response = local_server.make_call(requests.get, '/', headers={'authorization': 'allow'})
        assert response.status_code == 200
        assert ms._entry('wrong', 'GET') is None
        assert ms._entry('content', 'GET') is not None
        assert ms._entry('content/value', 'GET') is not None
        assert ms._entry('content/value/other', 'GET') is not None
        assert ms._entry('content/value/other/wrong', 'GET') is None
        assert ms._entry('/product/TRANSPORT', 'GET') is not None


def auth_external(auth_request):
    return auth_request.token == 'allow'