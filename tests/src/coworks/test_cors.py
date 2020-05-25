import requests

from coworks.config import Config, CORSConfig
from .tech_ms import *


class NoneCorsMS(TechMicroService):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self):
        """Root access."""
        return "get"


def test_authorize_none(local_server_factory):
    ms = NoneCorsMS()
    local_server = local_server_factory(ms)
    response = local_server.make_call(requests.options, '/', timeout=500)
    assert response.status_code == 200
    assert 'Access-Control-Allow-Origin' not in response.headers


class AllCorsMS(TechMicroService):

    def __init__(self, **kwargs):
        config = Config(cors=CORSConfig(allow_origin='*'))
        super().__init__(config=config, **kwargs)

    def get(self):
        """Root access."""
        return "get"


def test_authorize_all(local_server_factory):
    ms = AllCorsMS()
    local_server = local_server_factory(ms)
    response = local_server.make_call(requests.options, '/')
    assert response.status_code == 200
    assert response.headers['Access-Control-Allow-Origin'] == '*'


class OneCorsMS(TechMicroService):

    def __init__(self, **kwargs):
        config = Config(cors=CORSConfig(allow_origin='www.test.fr'))
        super().__init__(config=config, **kwargs)

    def get(self):
        """Root access."""
        return "get"


def test_authorize_one(local_server_factory):
    ms = OneCorsMS()
    local_server = local_server_factory(ms)
    response = local_server.make_call(requests.options, '/')
    assert response.status_code == 200
    assert response.headers['Access-Control-Allow-Origin'] == 'www.test.fr'


class SeveralCorsMS(TechMicroService):

    def __init__(self, **kwargs):
        config = Config(cors=CORSConfig(allow_origin=['www.test.fr', 'www.test.com']))
        super().__init__(config=config, **kwargs)

    def get(self):
        """Root access."""
        return "get"


def test_authorize_several(local_server_factory):
    ms = SeveralCorsMS()
    local_server = local_server_factory(ms)
    response = local_server.make_call(requests.options, '/')
    assert response.status_code == 200
    assert response.headers['Access-Control-Allow-Origin'] == 'www.test.fr, www.test.com'


class OtherCorsMS(TechMicroService):

    def __init__(self, **kwargs):
        config = Config(cors=CORSConfig(allow_origin='https://www.test.fr',
                                        allow_headers=['X-Special-Header'],
                                        max_age=600,
                                        expose_headers=['X-Special-Header'],
                                        allow_credentials=True))
        super().__init__(config=config, **kwargs)

    def get(self):
        """Root access."""
        return "get"


def test_authorize_other(local_server_factory):
    ms = OtherCorsMS()
    local_server = local_server_factory(ms)
    response = local_server.make_call(requests.options, '/')
    assert response.status_code == 200
    assert response.headers['Access-Control-Allow-Origin'] == 'https://www.test.fr'
    assert response.headers['Access-Control-Max-Age'] == '600'
