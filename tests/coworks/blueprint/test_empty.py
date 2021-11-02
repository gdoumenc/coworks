from coworks import Blueprint, entry
from tests.coworks.ms import TechMS


class BP(Blueprint):

    @entry
    def get(self):
        return f"blueprint test"


class TestClass:
    def test_request(self):
        app = TechMS()
        app.register_blueprint(BP("bp"))
        with app.test_client() as c:
            response = c.get('/', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == 'blueprint test'
