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
    fact.create('sfn_name1', 'every1', Every(5, Every.MINUTES), input=None)
    assert len(fact.triggers) == 1
    assert fact.triggers[0]['source'] == 'every'
    assert fact.triggers[0]['value'] == 'rate(5 minutes)'
    fact.create('sfn_name2', 'at2', At('0/10', '*', day_of_month='?', day_of_week='MON-FRI'), input=None)
    assert len(fact.triggers) == 2
    assert fact.triggers[1]['source'] == 'at'
    assert fact.triggers[1]['value'] == 'cron(0/10 * ? None MON-FRI None)'
    assert [t['name'] for t in fact.triggers] == ['sfn_name1_every1', 'sfn_name2_at2']


def test_biz_triggers():
    biz = BizMS()
    biz.react('every', Every(5, Every.MINUTES))
    biz.__sfn_client__ = MagicMock()
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
    biz.__sfn_client__ = MagicMock()
    biz.sfn_client.list_state_machines = \
        MagicMock(return_value={'stateMachines': [{'name': 'test', 'stateMachineArn': 'arn'}]})

    biz({'detail-type': 'Scheduled Event',
         'resources': ['arn:aws:events:eu-west-1:123456789:rule/test_every2']}, {})
    biz.sfn_client.start_execution.assert_called_once_with(input='{"key": "value"}', stateMachineArn='arn')

    assert len(biz.triggers) == 2
    assert [t['name'] for t in biz.triggers] == ['every', 'every2']
    assert [t['value'] for t in biz.triggers] == ['rate(5 minutes)', 'rate(10 hours)']
