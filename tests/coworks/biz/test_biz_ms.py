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
        assert str(execinfo.value.args[0]) == 'Biz microservice test already defined for step_function'
        fact.create('test2', At(5, 10, day_of_week='*'))
        assert len(fact.trigger_sources) == 2
        assert fact.trigger_sources[1]['name'] == 'step_function-test2'
        assert fact.trigger_sources[1]['source'] == 'at'
        assert fact.trigger_sources[1]['value'] == 'cron(5 10 None None * None)'
