import json

import requests

from coworks import Admin
from .tech_ms import *


class DoumentedMS(TechMS):

    def get(self):
        """Root access."""
        return "get"

    def post_content(self, value: int, other: str = "none"):
        """Add content."""
        return f"post_content {value}{other}"


def test_documentation(local_server_factory):
    ms = DoumentedMS()
    ms.register_blueprint(Admin(), url_prefix="/admin")
    local_server = local_server_factory(ms)
    response = local_server.make_call(requests.get, '/admin/routes')
    assert response.status_code == 200
    assert json.loads(response.text)["/"] == {
        "GET": {
            "doc": "Root access.",
            "signature": "(self)"
        }
    }
    assert json.loads(response.text)["/content/{_0}"] == {
        "POST": {
            "doc": "Add content.",
            "signature": "(self, value: int, other: str = \'none\')"
        }
    }
    assert json.loads(response.text)["/admin/routes"] == {
        "GET": {
            "doc": 'Returns the list of entrypoints with signature.',
            "signature": "(self)"
        }
    }
