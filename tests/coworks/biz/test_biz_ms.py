import os
from unittest.mock import Mock

import pytest

from coworks import BizFactory, Every, At
from coworks.config import Config


class TestClass:

    def test_biz_reactor(self):
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

    def test_biz_factory(self):
        fact = BizFactory('sfn_name1', configs=[Config(workspace='test')])
        fact.__sfn_client__ = Mock()
        fact.__sfn_arn__ = "arn1"
        os.environ['WORKSPACE'] = 'test'

        test_config_1 = Config(
            workspace="test",
            data={"key1": "value1"}
        )

        test_config_2 = Config(
            workspace="test",
            data={"key2": "value2"}
        )

        biz_1 = fact.create('every1', Every(5, Every.MINUTES), configs=[test_config_1])
        assert len(fact.biz) == 1
        assert len(fact.trigger_sources) == 1
        assert 'every1' in fact.biz
        biz_2 = fact.create('at2', At('0/10', '*', day_of_month='?', day_of_week='MON-FRI'), configs=[test_config_2])
        assert len(fact.biz) == 2
        assert len(fact.trigger_sources) == 2
        assert 'at2' in fact.biz

        biz_1({'detail-type': 'Scheduled Event',
               'resources': ['arn:aws:events:eu-west-1:123456789:rule/sfn_name1-every1']}, {})
        fact.sfn_client.start_execution.assert_called_once_with(input='{"key1": "value1"}', stateMachineArn='arn1')
        biz_2({'detail-type': 'Scheduled Event',
               'resources': ['arn:aws:events:eu-west-1:123456789:rule/sfn_name1-at2']}, {})
        fact.sfn_client.start_execution.assert_called_with(input='{"key2": "value2"}', stateMachineArn='arn1')

    def test_biz_data(self):
        os.environ['WORKSPACE'] = 'test'
        fact = BizFactory(sfn_name='step_function')
        fact.__sfn_client__ = Mock()
        fact.__sfn_arn__ = "arn"

        test_config_1 = Config(
            workspace="test",
            data={}
        )

        test_config_2 = Config(
            workspace="test",
            data={"key": "value"}
        )

        biz = fact.create('every1', Every(5, Every.MINUTES), configs=[test_config_1])
        biz({'detail-type': 'Scheduled Event',
             'resources': ['arn:aws:events:eu-west-1:123456789:rule/step_function-every1']}, {})
        fact.sfn_client.start_execution.assert_called_once_with(input='{}', stateMachineArn='arn')

        biz = fact.create('every2', Every(10, Every.HOURS), configs=[test_config_2])
        biz({'detail-type': 'Scheduled Event',
             'resources': ['arn:aws:events:eu-west-1:123456789:rule/step_function-every2']}, {})

        fact.sfn_client.start_execution.assert_called_with(input='{"key": "value"}', stateMachineArn='arn')

        assert len(fact.trigger_sources) == 2
        assert [t['name'] for t in fact.trigger_sources] == ['step_function-every1', 'step_function-every2']
        assert [t['value'] for t in fact.trigger_sources] == ['rate(5 minutes)', 'rate(10 hours)']
