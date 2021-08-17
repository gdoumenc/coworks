import typing as t

from flask import Blueprint as FlaskBlueprint, Flask, Response

from .config import Config
from .testing import CoworksClient


def entry(fun: t.Callable) -> t.Callable:
    ...


class CoworksResponse(Response):
    @property
    def text(self) -> str: ...


class CoworksMixin:
    current_app: "TechMicroService"


class Blueprint(CoworksMixin, FlaskBlueprint, ...):
    def __init__(self, name: str = None): ...


class TechMicroService(CoworksMixin, Flask):
    configs: t.List[Config]
    routes: t.List[str]

    def __init__(self, name: str = None, *, configs: t.Union[Config, t.List[Config]] = None, **kwargs): ...

    def test_client(self, use_cookies: bool = True, **kwargs: t.Any) -> CoworksClient: ...
