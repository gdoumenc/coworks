import io
import json

import pytest

from coworks import TechMicroService, BizFactory
from coworks.cli.sfn import StepFunctionWriter, TechState
from coworks.cli.writer import WriterError


class TechMS(TechMicroService):
    def __init__(self):
        super().__init__(app_name='test')

    def get_test(self):
        return "get"

    def get_params(self, value, other):
        return f"get {value} and {other}"

    def get_params_(self, value=1, other=2):
        return f"get {value} and {other}"

    def post_params(self, value=1, other=2):
        return f"get {value} and {other}"


def test_no_params():
    tech = TechMS()

    data = {'get': '/test'}
    call = TechState.get_call_data(None, data)
    res = tech(call, {})
    assert res['statusCode'] == 200


def test_arg_params():
    tech = TechMS()

    uri_params = {'_0': 1, '_1': 2}
    data = {'get': '/params/{_0}/{_1}', 'uri_params': uri_params}
    call = TechState.get_call_data(None, data)
    res = tech(call, {})
    assert res['statusCode'] == 200
    assert res['body'] == "get 1 and 2"


def test_kwargs_params():
    tech = TechMS()

    data = {'get': '/params'}
    call = TechState.get_call_data(None, data)
    res = tech(call, {})
    assert res['statusCode'] == 200
    assert res['body'] == "get 1 and 2"

    query_params = {'value': [3], 'other': [4]}
    data = {'get': '/params', 'query_params': query_params}
    call = TechState.get_call_data(None, data)
    res = tech(call, {})
    assert res['statusCode'] == 200
    assert res['body'] == "get 3 and 4"

    query_params = {'value': [5], 'other': [6]}
    data = {'post': '/params', 'query_params': query_params}
    call = TechState.get_call_data(None, data)
    res = tech(call, {})
    assert res['statusCode'] == 200
    assert res['body'] == "get 5 and 6"

    body = {'value': 7, 'other': 8}
    data = {'post': '/params', 'body': body}
    call = TechState.get_call_data(None, data)
    res = tech(call, {})
    assert res['statusCode'] == 200
    assert res['body'] == "get 7 and 8"


def test_biz_empty():
    biz = BizFactory()
    biz.create('test/biz/empty', 'test')
    writer = StepFunctionWriter(biz)
    output = io.StringIO()
    with pytest.raises(WriterError):
        writer.export(output=output, error=output)
    output.seek(0)
    res = output.read()
    assert res == "Error in test/biz/empty: The content of the test/biz/empty microservice seems to be empty.\n"


def test_biz_complete():
    biz = BizFactory()
    biz.create('test/biz/complete', 'test')
    writer = StepFunctionWriter(biz)
    output = io.StringIO()
    writer.export(output=output, error=output)
    output.seek(0)
    source = json.loads(output.read())
    assert source['Version'] == "1.0"
    assert 'Comment' in source
    assert len(source['States']) == 4

    states = source['States']
    data = states['Init']['Result']
    print(data)

    state = states['Check server']
    assert state is not None
    assert state['Type'] == 'Task'

    state = states['Send mail']
    assert state is not None
    assert state['Type'] == 'Task'
    assert state['End'] == True
