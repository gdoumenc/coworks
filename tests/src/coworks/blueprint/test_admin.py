import json

import requests

from coworks import Blueprint
from coworks.blueprint import Admin
from tests.src.coworks.tech_ms import *


class DocumentedMS(TechMS):

    def get(self):
        """Root access."""
        return "get"

    def post_content(self, value, other="none"):
        """Add content."""
        return f"post_content {value}{other}"

    def post_contentannotated(self, value: int, other: str = "none"):
        """Add content."""
        return f"post_content {value}{other}"

    def get_list(self, values: [int]):
        """Tests list param."""
        return "ok"


class HiddenBlueprint(Blueprint):

    def get(self):
        """Test not in routes."""
        return "ok"


class TestClass:
    def test_documentation(self, local_server_factory):
        ms = DocumentedMS()
        ms.register_blueprint(Admin(), url_prefix="/admin")
        local_server = local_server_factory(ms)
        response = local_server.make_call(requests.get, '/admin/routes', timeout=500)
        assert response.status_code == 200
        routes = json.loads(response.text)
        assert routes["/"] == {
            "GET": {
                "doc": "Root access.",
                "signature": "()"
            }
        }
        assert routes["/content/{_0}"] == {
            "POST": {
                "doc": "Add content.",
                "signature": "(value, other=none)"
            }
        }
        assert routes["/contentannotated/{_0}"] == {
            "POST": {
                "doc": "Add content.",
                "signature": "(value:<class 'int'>, other:<class 'str'>=none)"
            }
        }
        assert routes["/admin/routes"] == {
            "GET": {
                "doc": 'Returns the list of entrypoints with signature.',
                "signature": "()"
            }
        }
        assert routes["/list/{_0}"] == {
            "GET": {
                "doc": 'Tests list param.',
                "signature": "(values:[<class 'int'>])"
            }
        }

    def test_documentation(self, local_server_factory):
        ms = DocumentedMS()
        ms.register_blueprint(Admin(), url_prefix="/admin")
        ms.register_blueprint(HiddenBlueprint(), url_prefix="/hidden", hide_routes=True)
        local_server = local_server_factory(ms)
        response = local_server.make_call(requests.get, '/admin/routes', timeout=500)
        assert response.status_code == 200
        routes = json.loads(response.text)
        assert '/hidden' not in routes
