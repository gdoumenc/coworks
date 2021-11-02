from tests.coworks.blueprint.blueprint import BP, InitBP
from tests.coworks.ms import SimpleMS


class TestClass:

    def test_request(self):
        app = SimpleMS()
        app.register_blueprint(BP())
        with app.test_client() as c:
            response = c.get('/', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == 'get'
            response = c.get('/test/3', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "blueprint BP 3"
            response = c.get('/extended/test/3', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == 'blueprint extended test 3'

    def test_prefix(self):
        app = SimpleMS()
        app.register_blueprint(BP(), url_prefix="/prefix")
        with app.test_client() as c:
            response = c.get('/prefix/test/3', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "blueprint BP 3"
            response = c.get('/prefix/extended/test/3', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == 'blueprint extended test 3'

    def test_before_activation(self):
        app = SimpleMS()
        init_bp = InitBP()
        app.register_blueprint(init_bp, url_prefix="/prefix")
        with app.test_client() as c:
            response = c.get('/prefix/test/3', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "blueprint BP 3"
            init_bp.do_before_first_activation.assert_called_once()
            init_bp.do_before_activation.assert_called_once()
            init_bp.do_after_activation.assert_called_once()
