import requests
from unittest.mock import Mock

from tests.src.coworks.blueprint.blueprint import BP
from tests.src.coworks.tech_ms import SimpleMS


class TestClass:
    def test_request(self, local_server_factory):
        ms = SimpleMS()
        ms.register_blueprint(BP(import_name="blueprint"))
        local_server = local_server_factory(ms)
        response = local_server.make_call(requests.get, '/')
        assert response.status_code == 200
        assert response.text == 'get'
        response = local_server.make_call(requests.get, '/test/3')
        assert response.status_code == 200
        assert response.text == 'blueprint test 3'
        response = local_server.make_call(requests.get, '/extended/test/3')
        assert response.status_code == 200
        assert response.text == 'blueprint extended test 3'

    def test_prefix(self, local_server_factory):
        ms = SimpleMS()
        ms.register_blueprint(BP(), url_prefix="/prefix")
        local_server = local_server_factory(ms)
        response = local_server.make_call(requests.get, '/prefix/test/3')
        assert response.status_code == 200
        assert response.text == 'blueprint test 3'
        response = local_server.make_call(requests.get, '/prefix/extended/test/3')
        assert response.status_code == 200
        assert response.text == 'blueprint extended test 3'

    def test_before_activation(self, local_server_factory):
        ms = SimpleMS()
        init_bp = InitBP()
        ms.register_blueprint(init_bp, url_prefix="/prefix")
        local_server = local_server_factory(ms)
        response = local_server.make_call(requests.get, '/prefix/test/3')
        assert response.status_code == 200
        assert response.text == 'blueprint test 3'
        init_bp.do_before_first_activation.assert_called_once()
        init_bp.do_before_activation.assert_called_once()
        init_bp.do_after_activation.assert_called_once()


class InitBP(BP):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_before_first_activation = Mock()
        self.do_before_activation = Mock()
        self.do_after_activation = Mock()

        @self.before_first_activation
        def before_first_activation(event, context):
            self.do_before_first_activation(event, context)

        @self.before_activation
        def before_activation(event, context):
            self.do_before_activation(event, context)

        @self.after_activation
        def after_activation(response):
            self.do_after_activation(response)
            return response
