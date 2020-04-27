from unittest.mock import Mock, MagicMock

import pytest

from coworks import BizFactory, Every, At


def test_biz_reactor():
    fact = BizFactory('step_function')
    fact.create('test', Every(5, Every.MINUTES))
    assert len(fact.trigger_sources) == 1
    assert fact.trigger_sources[0]['name'] == 'step_function-test'
    assert fact.trigger_sources[0]['source'] == 'every'
    assert fact.trigger_sources[0]['value'] == 'rate(5 minutes)'
    with pytest.raises(Exception) as execinfo:
        fact.create('test', At(5, 10))
    assert len(fact.trigger_sources) == 1
    assert str(execinfo.value.args[0]) == 'BadRequestError: Biz microservice test already defined for step_function'
    fact.create('test2', At(5, 10, day_of_week='*'))
    assert len(fact.trigger_sources) == 2
    assert fact.trigger_sources[1]['name'] == 'step_function-test2'
    assert fact.trigger_sources[1]['source'] == 'at'
    assert fact.trigger_sources[1]['value'] == 'cron(5 10 None None * None)'


def test_biz_factory_undefined():
    fact = BizFactory('sfn_name')
    fact.__sfn_client__ = Mock()
    fact.sfn_client.list_state_machines = \
        MagicMock(return_value={'stateMachines': [
            {'name': 'sfn_name1', 'stateMachineArn': 'arn1'},
            {'name': 'sfn_name2', 'stateMachineArn': 'arn2'}
        ], 'nextToken': None})

    with pytest.raises(Exception) as execinfo:
        fact({'detail-type': 'Scheduled Event',
              'resources': ['arn:aws:events:eu-west-1:123456789:rule/sfn_name-every1']}, {})
    assert str(execinfo.value.args[0]) == 'BadRequestError: Undefined step function : sfn_name'

    fact = BizFactory('sfn_name')
    fact.__sfn_client__ = Mock()
    fact.sfn_client.list_state_machines = \
        MagicMock(return_value={'stateMachines': [
            {'name': 'sfn_name', 'stateMachineArn': 'arn1'},
            {'name': 'sfn_name2', 'stateMachineArn': 'arn2'}
        ], 'nextToken': None})
    with pytest.raises(Exception) as execinfo:
        fact({'detail-type': 'Scheduled Event',
              'resources': ['arn:aws:events:eu-west-1:123456789:rule/sfn_name-every1']}, {})
    assert str(execinfo.value.args[0]) == 'BadRequestError: Unregistered biz : every1'

    fact.create('every', Every(5, Every.MINUTES), data={"key1": "value1"})
    with pytest.raises(Exception) as execinfo:
        fact({'detail-type': 'Scheduled Event',
              'resources': ['arn:aws:events:eu-west-1:123456789:rule/sfn_name-every1']}, {})
    assert str(execinfo.value.args[0]) == 'BadRequestError: Unregistered biz : every1'


def test_biz_factory():
    fact = BizFactory('sfn_name1')
    fact.__sfn_client__ = Mock()
    fact.__sfn_arn__ = "arn1"

    fact.create('every1', Every(5, Every.MINUTES), data={"key1": "value1"})
    assert len(fact.biz) == 1
    assert len(fact.trigger_sources) == 1
    assert 'every1' in fact.biz
    fact.create('at2', At('0/10', '*', day_of_month='?', day_of_week='MON-FRI'), data={"key2": "value2"})
    assert len(fact.biz) == 2
    assert len(fact.trigger_sources) == 2
    assert 'at2' in fact.biz

    fact({'detail-type': 'Scheduled Event',
          'resources': ['arn:aws:events:eu-west-1:123456789:rule/sfn_name1-every1']}, {})
    fact.sfn_client.start_execution.assert_called_once_with(input='{"key1": "value1"}', stateMachineArn='arn1')
    fact({'detail-type': 'Scheduled Event',
          'resources': ['arn:aws:events:eu-west-1:123456789:rule/sfn_name1-at2']}, {})
    fact.sfn_client.start_execution.assert_called_with(input='{"key2": "value2"}', stateMachineArn='arn1')


def test_biz_data():
    fact = BizFactory('step_function')
    fact.__sfn_client__ = Mock()
    fact.__sfn_arn__ = "arn"

    fact.create('every1', Every(5, Every.MINUTES))
    fact({'detail-type': 'Scheduled Event',
          'resources': ['arn:aws:events:eu-west-1:123456789:rule/step_function-every1']}, {})
    fact.sfn_client.start_execution.assert_called_once_with(input='{}', stateMachineArn='arn')
    fact.create('every2', Every(10, Every.HOURS), data={'key': 'value'})
    fact({'detail-type': 'Scheduled Event',
          'resources': ['arn:aws:events:eu-west-1:123456789:rule/step_function-every2']}, {})
    fact.sfn_client.start_execution.assert_called_with(input='{"key": "value"}', stateMachineArn='arn')

    assert len(fact.trigger_sources) == 2
    assert [t['name'] for t in fact.trigger_sources] == ['step_function-every1', 'step_function-every2']
    assert [t['value'] for t in fact.trigger_sources] == ['rate(5 minutes)', 'rate(10 hours)']
