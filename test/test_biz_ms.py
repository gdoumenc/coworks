from unittest.mock import MagicMock

import pytest
from coworks import BizFactory, Every, At

from .biz_ms import *


def test_biz_reactor():
    biz = BizMS()
    biz.add_reactor('test', Every(5, Every.MINUTES))
    assert len(biz.trigger_sources) == 1
    assert biz.trigger_sources[0]['name'] == 'step_function-test'
    assert biz.trigger_sources[0]['source'] == 'every'
    assert biz.trigger_sources[0]['value'] == 'rate(5 minutes)'
    with pytest.raises(Exception) as execinfo:
        biz.add_reactor('test', At(5, 10))
    assert len(biz.trigger_sources) == 1
    assert str(execinfo.value.args[0]) == 'Reactor test already defined for step_function.'
    biz.add_reactor('test2', At(5, 10, day_of_week='*'))
    assert len(biz.trigger_sources) == 2
    assert biz.trigger_sources[1]['name'] == 'step_function-test2'
    assert biz.trigger_sources[1]['source'] == 'at'
    assert biz.trigger_sources[1]['value'] == 'cron(5 10 None None * None)'


def test_biz_factory():
    fact = BizFactory()
    fact.__sfn_client__ = MagicMock()

    sfn1 = fact.create('sfn_name1', 'every1', Every(5, Every.MINUTES),
                       data={"key1": "value1"})
    assert len(fact.services) == 1
    assert len(fact.trigger_sources) == 1
    assert 'sfn_name1-every1' in fact.services
    sfn2 = fact.create('sfn_name2', 'at2', At('0/10', '*', day_of_month='?', day_of_week='MON-FRI'),
                       data={"key2": "value2"})
    assert len(fact.services) == 2
    assert len(fact.trigger_sources) == 2
    assert 'sfn_name2-at2' in fact.services

    sfn1.__sfn_client__ = MagicMock()
    sfn1.sfn_client.list_state_machines = \
        MagicMock(return_value={'stateMachines': [
            {'name': 'sfn_name1', 'stateMachineArn': 'arn1'},
            {'name': 'sfn_name2', 'stateMachineArn': 'arn2'}
        ], 'nextToken': None})

    with pytest.raises(Exception) as execinfo:
        fact({'detail-type': 'Scheduled Event',
              'resources': ['arn:aws:events:eu-west-1:123456789:rule/every1']}, {})
    assert str(execinfo.value.args[0]) == 'BadRequestError: Unregistered reactor : every1'

    fact({'detail-type': 'Scheduled Event',
          'resources': ['arn:aws:events:eu-west-1:123456789:rule/sfn_name1-every1']}, {})
    sfn1.sfn_client.start_execution.assert_called_once_with(input='{"key1": "value1"}', stateMachineArn='arn1')

    sfn2.__sfn_client__ = MagicMock()
    sfn2.sfn_client.list_state_machines = \
        MagicMock(return_value={'stateMachines': [
            {'name': 'sfn_name1', 'stateMachineArn': 'arn1'},
            {'name': 'sfn_name2', 'stateMachineArn': 'arn2'}
        ], 'nextToken': None})
    fact({'detail-type': 'Scheduled Event',
          'resources': ['arn:aws:events:eu-west-1:123456789:rule/sfn_name2-at2']}, {})
    sfn2.sfn_client.start_execution.assert_called_once_with(input='{"key2": "value2"}', stateMachineArn='arn2')


def test_biz_triggers():
    biz = BizMS()
    biz.__sfn_client__ = MagicMock()

    biz.add_reactor('every', Every(5, Every.MINUTES))
    biz.sfn_client.list_state_machines = \
        MagicMock(return_value={'stateMachines': [{'name': 'other', 'stateMachineArn': 'arn'}], 'nextToken': None})

    with pytest.raises(Exception) as execinfo:
        biz({'detail-type': 'Scheduled Event',
             'resources': ['arn:aws:events:eu-west-1:123456789:rule/step_function-every']}, {})
    assert str(execinfo.value.args[0]) == 'BadRequestError: Undefined step function : step_function'

    biz.sfn_client.list_state_machines = \
        MagicMock(
            return_value={'stateMachines': [{'name': 'step_function', 'stateMachineArn': 'arn'}], 'nextToken': None})
    with pytest.raises(Exception) as execinfo:
        biz({'detail-type': 'Scheduled Event',
             'resources': ['arn:aws:events:eu-west-1:123456789:rule/step_function-reactor_name']}, {})
    assert str(execinfo.value.args[0]) == 'BadRequestError: Unregistered reactor : step_function-reactor_name'

    biz({'detail-type': 'Scheduled Event',
         'resources': ['arn:aws:events:eu-west-1:123456789:rule/step_function-every']}, {})
    biz.sfn_client.start_execution.assert_called_once_with(input='{}', stateMachineArn='arn')

    biz.add_reactor('every2', Every(10, Every.HOURS), data={'key': 'value'})
    biz.sfn_client.list_state_machines = \
        MagicMock(return_value={'stateMachines': [{'name': 'test', 'stateMachineArn': 'arn'}]})

    biz({'detail-type': 'Scheduled Event',
         'resources': ['arn:aws:events:eu-west-1:123456789:rule/step_function-every2']}, {})
    biz.sfn_client.start_execution.assert_called_with(input='{"key": "value"}', stateMachineArn='arn')

    assert len(biz.trigger_sources) == 2
    assert [t['name'] for t in biz.trigger_sources] == ['step_function-every', 'step_function-every2']
    assert [t['value'] for t in biz.trigger_sources] == ['rate(5 minutes)', 'rate(10 hours)']
