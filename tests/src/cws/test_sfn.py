import io
import json
from unittest.mock import Mock, MagicMock

import pytest
import yaml

from coworks import BizFactory
from coworks.cws import WriterError
from coworks.cws.writer.sfn import StepFunctionWriter, StepFunction, TechState
from tests.src.coworks.tech_ms import S3MockTechMS


class TestStepFunction(StepFunction):

    def __init__(self, data):
        filepath = Mock()
        file = MagicMock()
        file.__enter__ = Mock(return_value=data)
        filepath.open = Mock(return_value=file)
        with filepath.open() as file:
            self.data = yaml.load(file, Loader=yaml.SafeLoader)

        super().__init__("test", filepath)


class TechMS(S3MockTechMS):

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
    biz = BizFactory('tests/src/coworks/biz/empty')
    biz.create('test')
    writer = StepFunctionWriter(biz)
    output = io.StringIO()
    with pytest.raises(WriterError):
        writer.export(output=output, error=output)
    output.seek(0)
    res = output.read()
    assert res == "Error in tests/src/coworks/biz/empty: The content of the tests/src/coworks/biz/empty microservice " \
                  "seems to be empty.\n"


def test_biz_complete():
    """Tests the doc example."""
    fact = BizFactory('tests/src/coworks/biz/complete')
    fact.create('test')
    writer = StepFunctionWriter(fact)
    output = io.StringIO()
    writer.export(output=output, error=output)
    output.seek(0)
    source = json.loads(output.read())
    assert source['Version'] == "1.0"
    assert 'Comment' in source
    assert len(source['States']) == 4

    states = source['States']
    state = states['Check server']
    assert state is not None
    assert state['Type'] == 'Task'

    state = states['Send mail']
    assert state is not None
    assert state['Type'] == 'Task'
    assert state['End'] is True


def test_fail():
    data = {'states': [{
        'name': "fail",
        'fail': None
    }]}
    sfn = TestStepFunction(yaml.dump(data))
    sfn.generate()
    assert len(sfn.all_states) == 2
    assert 'End' not in sfn.all_states[1].state
    assert 'Cause' in sfn.all_states[1].state
    assert 'Error' in sfn.all_states[1].state


def test_pass():
    # missing key cases
    data = {'states': [{
        'name': "action",
        'pass': None
    }]}
    sfn = TestStepFunction(yaml.dump(data))
    sfn.generate()
    assert len(sfn.all_states) == 2
    assert 'End' in sfn.all_states[1].state


def test_tech():
    # missing key cases
    data = {'states': [{
        'name': "action",
        'tech': {
            'service': "tech",
        }
    }]}
    sfn = TestStepFunction(yaml.dump(data))
    with pytest.raises(WriterError) as pytest_wrapped_e:
        sfn.generate()
    assert pytest_wrapped_e.type == WriterError
    assert pytest_wrapped_e.value.args[0] == "No route defined for {'name': 'action', 'tech': {'service': 'tech'}}"

    data = {'states': [{
        'name': "action",
        'tech': {
            'get': "/",
        }
    }]}
    sfn = TestStepFunction(yaml.dump(data))
    with pytest.raises(WriterError) as pytest_wrapped_e:
        sfn.generate()
    assert pytest_wrapped_e.type == WriterError
    assert pytest_wrapped_e.value.args[0] == "The key service is missing for {'get': '/'}"

    data = {'states': [{
        'name': "action",
        'tech': {
            'service': "tech1",
            'get': "/",
            'post': "/",
        }
    }]}
    sfn = TestStepFunction(yaml.dump(data))
    with pytest.raises(WriterError) as pytest_wrapped_e:
        sfn.generate()
    assert pytest_wrapped_e.type == WriterError
    assert pytest_wrapped_e.value.args[0].startswith("Too many methods defined for ")


def test_catch_all():
    data = {'states': [{
        'name': "action",
        'tech': {
            'service': "tech1",
            'get': "/",
        }
    }], 'catch': [{'fail': None}]}
    sfn = TestStepFunction(yaml.dump(data))
    sfn.generate()
    assert len(sfn.all_states) == 4
    assert len(sfn.all_states[1].state['Catch']) == 1

    data = {'states': [{
        'name': "action",
        'tech': {
            'service': "tech1",
            'get': "/",
        },
        'catch': [{'fail': None}]
    }], 'catch': [{'fail': None}]}
    sfn = TestStepFunction(yaml.dump(data))
    sfn.generate()
    assert len(sfn.all_states) == 5
    assert len(sfn.all_states[1].state['Catch']) == 2


def test_list():
    data = {'states': [{
        'name': "action 1",
        'tech': {
            'service': "tech",
            'get': "/",
        }
    }, {
        'name': "action 2",
        'tech': {
            'service': "tech",
            'get': "/",
        }
    }]}
    sfn = TestStepFunction(yaml.dump(data))
    sfn.generate()
    assert 'Next' in sfn.all_states[1].state
    assert sfn.all_states[1].state['Next'] == sfn.all_states[2].name
    assert 'End' in sfn.all_states[2].state


def test_choice():
    # missing key cases
    data = {'states': [{
        'name': "action",
        'choices': None
    }]}
    sfn = TestStepFunction(yaml.dump(data))
    with pytest.raises(WriterError):
        sfn.generate()

    data = {'states': [{
        'name': "action",
        'choices': [{
            'var': '', 'oper': '', 'value': '', 'goto': 'Step'
        }]
    }, {
        'name': "Step",
        'pass': None
    }]}
    sfn = TestStepFunction(yaml.dump(data))
    sfn.generate()
    assert len(sfn.all_states) == 3
    assert 'Default' in sfn.all_states[1].state
    assert 'End' in sfn.all_states[2].state
