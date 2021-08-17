from typing import Any

from flask.testing import FlaskClient
from .coworks import CoworksResponse


class CoworksClient(FlaskClient):
    def get(self, *args: Any, **kw: Any) -> CoworksResponse: ...

    def post(self, *args: Any, **kw: Any) -> CoworksResponse: ...

    def put(self, *args: Any, **kw: Any) -> CoworksResponse: ...

    def _add_params(self, url: str, params: dict = None) -> str: ...
