from unittest import mock
from unittest.mock import MagicMock

from coworks import TechMicroService
from coworks import entry
from coworks.config import Config
from ..event import get_event


class AsyncMS(TechMicroService):

    @entry
    def get(self):
        return "ok"


class TestClass:
    def test_async_store(self, empty_context):
        with mock.patch('boto3.session.Session') as session:
            session.side_effect = lambda: session
            session.client = MagicMock(side_effect=lambda _: session.client)
            app = AsyncMS()
            with app.cws_client() as c:
                event = get_event('/', 'get')
                event['headers']['InvocationType'.lower()] = 'Event'
                event['headers'][Config.bizz_bucket_header_key.lower()] = 'bucket'
                event['headers'][Config.bizz_key_header_key.lower()] = 'specific/key'
                app(event, empty_context)
                session.assert_called_once()
                session.client.assert_called_once_with('s3')
                session.client.upload_fileobj.assert_called_once()
