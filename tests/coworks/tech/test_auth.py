from coworks import entry
from tests.coworks.blueprint.blueprint import BP
from tests.coworks.ms import SimpleMS


def get_event(token):
    return {
        'type': 'TOKEN',
        'methodArn': 'arn:aws:execute-api:eu-west-1:935392763270:htzd2rneg1/dev/GET/',
        'authorizationToken': token
    }


class AuthorizeAll(SimpleMS):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_blueprint(BP(), url_prefix="/blueprint")

    def token_authorizer(self, token):
        return True

    @entry
    def get_product(self, ref):
        return ref


class AuthorizeNothing(AuthorizeAll):

    def token_authorizer(self, token):
        return False


class AuthorizedMS(AuthorizeAll):

    def token_authorizer(self, token):
        return token == 'token'


class TestClass:
    def test_authorize_all(self, empty_context):
        app = AuthorizeAll()
        with app.app_context() as c:
            response = app(get_event('token'), empty_context)
            assert response['principalId'] == 'user'
            assert response['policyDocument']['Statement'][0]['Effect'] == 'Allow'

    def test_authorize_nothing(self, empty_context):
        app = AuthorizeNothing()
        with app.app_context() as c:
            response = app(get_event('token'), empty_context)
            assert response['principalId'] == 'user'
            assert response['policyDocument']['Statement'][0]['Effect'] == 'Deny'

    def test_authorized(self, empty_context):
        app = AuthorizedMS()
        with app.app_context() as c:
            response = app(get_event('wrong'), empty_context)
            assert response['principalId'] == 'user'
            assert response['policyDocument']['Statement'][0]['Effect'] == 'Deny'
            response = app(get_event('token'), empty_context)
            assert response['principalId'] == 'user'
            assert response['policyDocument']['Statement'][0]['Effect'] == 'Allow'
