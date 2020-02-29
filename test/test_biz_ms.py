from unittest.mock import MagicMock

import pytest
from coworks import BizFactory, Every, At

from .biz_ms import *


def test_biz_reactor():
    biz = BizMS()
    biz.react('test', Every(5, Every.MINUTES))
    assert len(biz.triggers) == 1
    assert biz.triggers[0]['source'] == 'every'
    assert biz.triggers[0]['value'] == 'rate(5 minutes)'
    with pytest.raises(Exception) as execinfo:
        biz.react('test', At(5, 10))
    assert len(biz.triggers) == 1
    assert str(execinfo.value.args[0]) == 'Reactor test already defined.'
    biz.react('test2', At(5, 10, day_of_week='*'))
    assert len(biz.triggers) == 2
    assert biz.triggers[1]['source'] == 'at'
    assert biz.triggers[1]['value'] == 'cron(5 10 None None * None)'


def test_biz_factory():
    fact = BizFactory()
    fact.__sfn_client__ = MagicMock()

    sfn1 = fact.create('sfn_name1', 'every1', Every(5, Every.MINUTES),
                       input={"key1": "value1"})
    assert len(fact.reactors) == 1
    assert 'every1' in fact.reactors
    sfn2 = fact.create('sfn_name2', 'at2', At('0/10', '*', day_of_month='?', day_of_week='MON-FRI'),
                       input={"key2": "value2"})
    assert len(fact.reactors) == 2
    assert 'at2' in fact.reactors

    sfn1.__sfn_client__ = MagicMock()
    sfn1.sfn_client.list_state_machines = \
        MagicMock(return_value={'stateMachines': [
            {'name': 'sfn_name1', 'stateMachineArn': 'arn1'},
            {'name': 'sfn_name2', 'stateMachineArn': 'arn2'}
        ], 'nextToken': None})
    fact({'detail-type': 'Scheduled Event',
          'resources': ['arn:aws:events:eu-west-1:123456789:rule/every1']}, {})
    sfn1.sfn_client.start_execution.assert_called_once_with(input='{"key1": "value1"}', stateMachineArn='arn1')

    sfn2.__sfn_client__ = MagicMock()
    sfn2.sfn_client.list_state_machines = \
        MagicMock(return_value={'stateMachines': [
            {'name': 'sfn_name1', 'stateMachineArn': 'arn1'},
            {'name': 'sfn_name2', 'stateMachineArn': 'arn2'}
        ], 'nextToken': None})
    fact({'detail-type': 'Scheduled Event',
          'resources': ['arn:aws:events:eu-west-1:123456789:rule/at2']}, {})
    sfn2.sfn_client.start_execution.assert_called_once_with(input='{"key2": "value2"}', stateMachineArn='arn2')


def test_biz_triggers():
    biz = BizMS()
    biz.__sfn_client__ = MagicMock()

    biz.react('every', Every(5, Every.MINUTES))
    biz.sfn_client.list_state_machines = \
        MagicMock(return_value={'stateMachines': [{'name': 'other', 'stateMachineArn': 'arn'}], 'nextToken': None})

    with pytest.raises(Exception) as execinfo:
        biz({'detail-type': 'Scheduled Event',
             'resources': ['arn:aws:events:eu-west-1:123456789:rule/test_test']}, {})
    assert str(execinfo.value.args[0]) == 'BadRequestError: Undefined step function : test'

    biz.sfn_client.list_state_machines = \
        MagicMock(return_value={'stateMachines': [{'name': 'test', 'stateMachineArn': 'arn'}], 'nextToken': None})
    with pytest.raises(Exception) as execinfo:
        biz({'detail-type': 'Scheduled Event',
             'resources': ['arn:aws:events:eu-west-1:123456789:rule/test_test']}, {})
    assert str(execinfo.value.args[0]) == 'BadRequestError: Unregistered reactor : test'

    biz({'detail-type': 'Scheduled Event',
         'resources': ['arn:aws:events:eu-west-1:123456789:rule/test_every']}, {})
    biz.sfn_client.start_execution.assert_called_once_with(input='{}', stateMachineArn='arn')

    biz.react('every2', Every(10, Every.HOURS), input={'key': 'value'})
    biz.sfn_client.list_state_machines = \
        MagicMock(return_value={'stateMachines': [{'name': 'test', 'stateMachineArn': 'arn'}]})

    biz({'detail-type': 'Scheduled Event',
         'resources': ['arn:aws:events:eu-west-1:123456789:rule/test_every2']}, {})
    biz.sfn_client.start_execution.assert_called_with(input='{"key": "value"}', stateMachineArn='arn')

    assert len(biz.triggers) == 2
    assert [t['name'] for t in biz.triggers] == ['every', 'every2']
    assert [t['value'] for t in biz.triggers] == ['rate(5 minutes)', 'rate(10 hours)']
