import requests

from .app import App


def test_simple_example(local_server_factory):
    local_server = local_server_factory(App())
    response = local_server.make_call(requests.get, '/')
    assert response.status_code == 200
    assert response.text == "Simple microservice for test.\n"
    response = local_server.make_call(requests.get, '/', params={"usage": "demo"})
    assert response.status_code == 200
    assert response.text == "Simple microservice for demo.\n"
    response = local_server.make_call(requests.get, '/value/1')
    assert response.status_code == 200
    assert response.text == "0\n"
    response = local_server.make_call(requests.put, '/value/1', json={"value": 456})
    assert response.status_code == 200
    assert response.text == "null"
    response = local_server.make_call(requests.get, '/value/1')
    assert response.status_code == 200
    assert response.text == "456\n"


def test_params(local_server_factory):
    local_server = local_server_factory(App())
    response = local_server.make_call(requests.put, '/value/1', json=456, timeout=100.5)
    assert response.status_code == 200
    assert response.text == "null"
    response = local_server.make_call(requests.get, '/value/1')
    assert response.status_code == 200
    assert response.text == "456\n"
