from coworks import Blueprint, entry
from tests.coworks.ms import TechMS


class EmptyBlueprint(Blueprint):

    @entry
    def get(self):
        return f"blueprint test"


class TestClass:

    def test_as_root(self):
        app = TechMS()
        app.register_blueprint(EmptyBlueprint("bp"))
        with app.test_client() as c:
            response = c.get('/', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == 'blueprint test'
            assert app.routes == ['/']

    def test_with_prefix(self):
        app = TechMS()
        app.register_blueprint(EmptyBlueprint("bp"), url_prefix='bp')
        with app.test_client() as c:
            response = c.get('/bp', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == 'blueprint test'
            assert app.routes == ['/bp']
