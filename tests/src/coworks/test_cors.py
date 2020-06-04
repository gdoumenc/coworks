import requests

from coworks.config import Config, CORSConfig
from .tech_ms import *


class NoneCorsMS(TechMicroService):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self):
        """Root access."""
        return "get"


class AllCorsMS(TechMicroService):

    def __init__(self, **kwargs):
        config = Config(cors=CORSConfig(allow_origin='*'))
        super().__init__(configs=config, **kwargs)

    def get(self):
        """Root access."""
        return "get"


class OneCorsMS(TechMicroService):

    def __init__(self, **kwargs):
        config = Config(cors=CORSConfig(allow_origin='www.test.fr'))
        super().__init__(configs=config, **kwargs)

    def get(self):
        """Root access."""
        return "get"


class SeveralCorsMS(TechMicroService):

    def __init__(self, **kwargs):
        config = Config(cors=CORSConfig(allow_origin=['www.test.fr', 'www.test.com']))
        super().__init__(configs=config, **kwargs)

    def get(self):
        """Root access."""
        return "get"


class OtherCorsMS(TechMicroService):

    def __init__(self, **kwargs):
        config = Config(cors=CORSConfig(allow_origin='https://www.test.fr',
                                        allow_headers=['X-Special-Header'],
                                        max_age=600,
                                        expose_headers=['X-Special-Header'],
                                        allow_credentials=True))
        super().__init__(configs=config, **kwargs)

    def get(self):
        """Root access."""
        return "get"


class TestClass:
    def test_authorize_none(self, local_server_factory):
        ms = NoneCorsMS()
        local_server = local_server_factory(ms)
        response = local_server.make_call(requests.options, '/', timeout=500)
        assert response.status_code == 200
        assert 'Access-Control-Allow-Origin' not in response.headers

    def test_authorize_all(self, local_server_factory):
        ms = AllCorsMS()
        local_server = local_server_factory(ms)
        response = local_server.make_call(requests.options, '/')
        assert response.status_code == 200
        assert response.headers['Access-Control-Allow-Origin'] == '*'

    def test_authorize_one(self, local_server_factory):
        ms = OneCorsMS()
        local_server = local_server_factory(ms)
        response = local_server.make_call(requests.options, '/')
        assert response.status_code == 200
        assert response.headers['Access-Control-Allow-Origin'] == 'www.test.fr'

    def test_authorize_several(self, local_server_factory):
        ms = SeveralCorsMS()
        local_server = local_server_factory(ms)
        response = local_server.make_call(requests.options, '/')
        assert response.status_code == 200
        assert response.headers['Access-Control-Allow-Origin'] == 'www.test.fr, www.test.com'

    def test_authorize_other(self, local_server_factory):
        ms = OtherCorsMS()
        local_server = local_server_factory(ms)
        response = local_server.make_call(requests.options, '/')
        assert response.status_code == 200
        assert response.headers['Access-Control-Allow-Origin'] == 'https://www.test.fr'
        assert response.headers['Access-Control-Max-Age'] == '600'
