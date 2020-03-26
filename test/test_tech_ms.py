import requests
import pytest

from .tech_ms import *
from coworks import Every, At


def test_request(local_server_factory):
    local_server = local_server_factory(SimpleMS())
    response = local_server.make_call(requests.get, '/')
    assert response.status_code == 200
    assert response.text == 'get'
    response = local_server.make_call(requests.post, '/')
    assert response.status_code == 405
    response = local_server.make_call(requests.get, '/get1')
    assert response.status_code == 403
    response = local_server.make_call(requests.get, '/content')
    assert response.status_code == 200
    assert response.text == "get content"
    response = local_server.make_call(requests.get, '/content/3')
    assert response.status_code == 200
    assert response.text == "get content with 3"
    response = local_server.make_call(requests.get, '/content/3/other')
    assert response.status_code == 200
    assert response.text == "get content with 3 and other"
    response = local_server.make_call(requests.post, '/content', json={"other": 'other'})
    assert response.status_code == 200
    assert response.text == "post content without value but other"
    response = local_server.make_call(requests.post, '/content/3', json={"other": 'other'})
    assert response.status_code == 200
    assert response.text == "post content with 3 and other"
    response = local_server.make_call(requests.post, '/content/3', json='other')
    assert response.status_code == 200
    assert response.text == "post content with 3 and other"
    response = local_server.make_call(requests.post, '/content/3', json={"other": 'other', "value": 5})
    assert response.status_code == 400

    response = local_server.make_call(requests.get, '/kwparam1', params={"value": 5})
    assert response.status_code == 200
    assert response.text == "get **param with only 5"
    response = local_server.make_call(requests.get, '/kwparam1', params={"other": 'other', "value": 5})
    assert response.status_code == 400
    response = local_server.make_call(requests.get, '/kwparam1', json={"value": 5})
    assert response.status_code == 200
    assert response.text == "get **param with only 5"
    response = local_server.make_call(requests.get, '/kwparam1', json={"other": 'other', "value": 5})
    assert response.status_code == 400
    response = local_server.make_call(requests.get, '/kwparam2', params={"other": 'other', "value": 5})
    assert response.status_code == 200
    assert response.text == "get **param with 5 and ['other']"
    response = local_server.make_call(requests.get, '/kwparam2', json={"other": 'other', "value": 5})
    assert response.status_code == 200
    assert response.text == "get **param with 5 and ['other']"

    response = local_server.make_call(requests.get, '/extended/content')
    assert response.status_code == 200
    assert response.text == "hello world"


def test_prefixed(local_server_factory):
    local_server = local_server_factory(PrefixedMS())
    response = local_server.make_call(requests.get, '/prefix')
    assert response.status_code == 200
    assert response.text == "hello world"
    response = local_server.make_call(requests.get, '/prefix/content')
    assert response.status_code == 200
    assert response.text == "hello world"
    response = local_server.make_call(requests.get, '/prefix/extended/content')
    assert response.status_code == 200
    assert response.text == "hello world"


def test_parameterized(local_server_factory):
    local_server = local_server_factory(ParamMS())
    response = local_server.make_call(requests.get, '/123')
    assert response.status_code == 200
    assert response.text == '123'
    response = local_server.make_call(requests.get, '/concat/123/456')
    assert response.status_code == 200
    assert response.text == '123456'
    response = local_server.make_call(requests.get, '/value')
    assert response.status_code == 200
    assert response.text == '123'
    response = local_server.make_call(requests.put, '/value', json={'value': "456"})
    assert response.status_code == 200
    assert response.text == '456'
    response = local_server.make_call(requests.get, '/value')
    assert response.status_code == 200
    assert response.text == '456'
    response = local_server.make_call(requests.get, '/param/test1')
    assert response.status_code == 200
    assert response.text == 'test1default1default2'
    response = local_server.make_call(requests.get, '/param/test1', params={"param1": "param1"})
    assert response.status_code == 200
    assert response.text == 'test1param1default2'
    response = local_server.make_call(requests.get, '/param/test1', params={"param2": "param2"})
    assert response.status_code == 200
    assert response.text == 'test1default1param2'
    response = local_server.make_call(requests.get, '/param/test1', params={"param1": "param1", "param2": "param2"})
    assert response.status_code == 200
    assert response.text == 'test1param1param2'
    response = local_server.make_call(requests.get, '/param/test1', params=[('param1', 'param1'), ('param1', 'param2')])
    assert response.status_code == 200
    assert response.text == "test1['param1', 'param2']default2"


def test_slug_parameterized(local_server_factory):
    local_server = local_server_factory(PrefixedParamMS())
    response = local_server.make_call(requests.get, '/prefix/123')
    assert response.status_code == 200
    assert response.text == '123'
    response = local_server.make_call(requests.get, '/prefix/concat/123/456')
    assert response.status_code == 200
    assert response.text == '123456'


def test_tuple_returned(local_server_factory):
    local_server = local_server_factory(TupleReturnedMS())
    response = local_server.make_call(requests.get, '/')
    assert response.status_code == 200
    assert response.text == 'ok'
    response = local_server.make_call(requests.get, '/resp/ok')
    assert response.status_code == 200
    assert response.text == 'ok'
    response = local_server.make_call(requests.get, '/error/test')
    assert response.status_code == 300
    assert response.text == 'test'


def test_after_before_request():
    simple = SimpleMS()
    evts = []

    @simple.before_first_request
    def always_first():
        evts.append("first")

    @simple.before_request
    def before():
        evts.append("before")

    @simple.after_request
    def always_first():
        evts.append("after")

    simple({}, {})
    simple({}, {})

    assert evts == ["first", "before", "after", "before", "after"]
