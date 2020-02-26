import requests

from .blueprint import *
from .tech_ms import *


def test_request(local_server_factory):
    ms = SimpleMS()
    ms.register_blueprint(BP(import_name="blueprint"))
    local_server = local_server_factory(ms)
    response = local_server.make_call(requests.get, '/')
    assert response.status_code == 200
    assert response.text == 'get'
    response = local_server.make_call(requests.get, '/test/3')
    assert response.status_code == 200
    assert response.text == 'blueprint test 3'
    response = local_server.make_call(requests.get, '/extended/test/3')
    assert response.status_code == 200
    assert response.text == 'blueprint extended test 3'


def test_prefix(local_server_factory):
    ms = SimpleMS()
    ms.register_blueprint(BP(), url_prefix="/prefix")
    local_server = local_server_factory(ms)
    response = local_server.make_call(requests.get, '/prefix/test/3')
    assert response.status_code == 200
    assert response.text == 'blueprint test 3'
    response = local_server.make_call(requests.get, '/prefix/extended/test/3')
    assert response.status_code == 200
    assert response.text == 'blueprint extended test 3'
