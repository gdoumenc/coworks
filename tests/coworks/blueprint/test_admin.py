from flask import json

from coworks import Blueprint
from coworks.blueprint import Admin
from tests.coworks.ms import *


class DocumentedMS(TechMS):

    def token_authorizer(self, token):
        return True

    @entry
    def get(self):
        """Root access."""
        return "get"

    @entry
    def post_content(self, value, other="none"):
        """Add content."""
        return f"post_content {value}{other}"

    @entry
    def post_contentannotated(self, value: int, other: str = "none"):
        """Add content."""
        return f"post_content {value}{other}"

    @entry
    def get_list(self, values: [int]):
        """Tests list param."""
        return "ok"


class HiddenBlueprint(Blueprint):

    @entry
    def get(self):
        """Test not in routes."""
        return "ok"


class TestClass:

    def test_routes(self):
        app = DocumentedMS()
        with app.test_request_context():
            assert len(app.routes) == 4
            assert '/' in app.routes
            assert '/content/<value>' in app.routes
            assert '/contentannotated/<value>' in app.routes
            assert '/list/<values>' in app.routes

    def test_documentation(self):
        app = DocumentedMS()
        app.register_blueprint(Admin(), url_prefix="/admin")
        with app.test_client() as c:
            response = c.get('/admin/route', headers={'Authorization': 'token'})
            assert response.status_code == 200
            routes = json.loads(response.get_data(as_text=True))
            assert routes["/"]['GET'] == {
                "doc": "Root access.",
                "signature": "()"
            }
            assert routes["/content/<value>"]['POST'] == {
                "doc": "Add content.",
                "signature": "(value, other=none)"
            }
            assert routes["/contentannotated/<value>"]['POST'] == {
                "doc": "Add content.",
                "signature": "(value:<class 'int'>, other:<class 'str'>=none)"
            }
            assert routes["/admin/route"]['GET'] == {
                "doc": 'Returns the list of entrypoints with signature.',
                "signature": "(pretty=False)"
            }
            assert routes["/list/<values>"]['GET'] == {
                "doc": 'Tests list param.',
                "signature": "(values:[<class 'int'>])"
            }

    def test_documentation_with_blueprints(self):
        app = DocumentedMS()
        app.register_blueprint(Admin(), url_prefix="/admin")
        app.register_blueprint(HiddenBlueprint(), url_prefix="/hidden", hide_routes=True)
        with app.test_client() as c:
            response = c.get('/admin/route', headers={'Authorization': 'token'})
            assert response.status_code == 200
            routes = json.loads(response.get_data(as_text=True))
            assert '/hidden' not in routes
