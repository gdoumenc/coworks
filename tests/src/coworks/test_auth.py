import requests
from chalice import AuthResponse

from coworks.config import Config
from .blueprint.blueprint import BP
from .tech_ms import SimpleMS


class AuthorizeAllMS(SimpleMS):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_blueprint(BP(), url_prefix="/blueprint")

    def auth(self, auth_request):
        return True


class AuthorizeNothingMSExeptBP(SimpleMS):

    def __init__(self):
        super().__init__()
        self.register_blueprint(BP(), url_prefix="/blueprint")

    def auth(self, auth_request):
        return False


class AuthorizeNothingMS(SimpleMS):

    def __init__(self):
        super().__init__()
        self.register_blueprint(BP(), url_prefix="/blueprint", authorizer=auth_external)

    def auth(self, auth_request):
        return False


class AuthorizedMS(SimpleMS):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_blueprint(BP(), url_prefix="/blueprint")

    def auth(self, auth_request):
        if auth_request.token == 'allow':
            return AuthResponse(routes=['/'], principal_id='user')
        return False


class AuthorizedMS2(SimpleMS):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_blueprint(BP(), url_prefix="/blueprint", authorizer=AuthorizedMS2.auth)

    def auth(self, auth_request):
        if auth_request.token == 'allow':
            return AuthResponse(routes=['/'], principal_id='user')
        return False


class TestClass:
    def test_authorize_all(self, local_server_factory):
        local_server = local_server_factory(AuthorizeAllMS())
        response = local_server.make_call(requests.get, '/', headers={'authorization': 'token'})
        assert response.status_code == 200
        assert response.text == 'get'
        response = local_server.make_call(requests.get, '/blueprint/test/3', headers={'authorization': 'token'})
        assert response.status_code == 200
        assert response.text == 'blueprint test 3'

    def test_authorize_nothing_except_bp(self, local_server_factory):
        local_server = local_server_factory(AuthorizeNothingMSExeptBP())
        response = local_server.make_call(requests.get, '/', headers={'authorization': 'token'})
        assert response.status_code == 403
        response = local_server.make_call(requests.get, '/blueprint/test/3', headers={'authorization': 'token'})
        assert response.status_code == 200

    def test_authorize_nothing(self, local_server_factory):
        local_server = local_server_factory(AuthorizeNothingMS())
        response = local_server.make_call(requests.get, '/', headers={'authorization': 'token'})
        assert response.status_code == 403
        response = local_server.make_call(requests.get, '/blueprint/test/3', headers={'authorization': 'token'})
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
        assert response.status_code == 200

    def test_authorized2(self, local_server_factory):
        local_server = local_server_factory(AuthorizedMS2())
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


def auth_external(self, auth_request):
    if auth_request.token == 'allow':
        return True
    return False
