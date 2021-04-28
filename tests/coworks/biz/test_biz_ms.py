import pytest
import requests

from tests.coworks.biz_ms import BizMS
from tests.coworks.test_ms import SimpleMS


@pytest.mark.wip
class TestClass:

    def test_ms(self, local_server_factory):
        tech = SimpleMS()

        with pytest.raises(NotImplementedError) as pytest_wrapped_e:
            @tech.schedule('rate(1 hour)', name='hourly', description="Test hourly.")
            def every_sample(name):
                return tech.get(name=name)

    def test_biz(self, local_server_factory):
        biz = BizMS()

        @biz.schedule('rate(1 hour)', name='hourly', description="Test hourly.")
        @biz.schedule('cron(00 15 * * ? *)', name="daily", description="Test daiy.")
        def every_sample(name):
            return biz.get(name=name)

        local_server = local_server_factory(biz)
        response = local_server.make_call(requests.get, '/')
        assert response.status_code == 200
        assert response.text == 'ok'

        assert len(biz.schedule_entries) == 2
