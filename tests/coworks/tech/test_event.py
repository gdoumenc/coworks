from unittest.mock import Mock

from coworks import TechMicroService
from coworks import entry
from tests.coworks.ms import GlobalMS
from tests.coworks.ms import SimpleMS
from ..event import get_event


class ErrorMS(TechMicroService):

    def __init__(self):
        super().__init__()
        self.err = Mock()

        @self.errorhandler(500)
        def handle(e):
            self.err(e)

    def token_authorizer(self, token):
        return True

    @entry
    def get(self):
        """Root access."""
        return "Error 404", 404

    @entry
    def get_exception(self):
        """Root access."""
        return int("a")


class TestClass:
    def test_request_arg(self, empty_context):
        app = SimpleMS()
        with app.app_context() as c:
            response = app(get_event('/', 'get'), empty_context)
            assert response['statusCode'] == 200
            assert response['body'] == "get"
            assert 'Content-Type' in response['headers']
            assert response['headers']['Content-Type'] == 'text/plain; charset=utf-8'
            assert 'Content-Length' in response['headers']
            assert response['headers']['Content-Length'] == str(len(response['body']))
            response = app(get_event('/', 'post'), empty_context)
            assert response['statusCode'] == 405
            response = app(get_event('/get1', 'get'), empty_context)
            assert response['statusCode'] == 404
            response = app(get_event('/content', 'get'), empty_context)
            assert response['statusCode'] == 200
            assert response['body'] == "get content"
            response = app(get_event('/content/3', 'get'), empty_context)
            assert response['statusCode'] == 200
            assert response['body'] == "get content with 3"
            response = app(get_event('/content/3/other', 'get'), empty_context)
            assert response['statusCode'] == 200
            assert response['body'] == "get content with 3 and other"
            response = app(get_event('/content', 'post', body={"other": 'other'}), empty_context)
            assert response['statusCode'] == 200
            assert response['body'] == "post content without value but other"
            response = app(get_event('/content/3', 'post', body={"other": 'other'}), empty_context)
            assert response['statusCode'] == 200
            assert response['body'] == "post content with 3 and other"
            response = app(get_event('/content/3', 'post', body="other"), empty_context)
            assert response['statusCode'] == 200
            assert response['body'] == "post content with 3 and other"
            response = app(get_event('/content/3', 'post', body={"other": 'other', "value": 5}), empty_context)
            assert response['statusCode'] == 400

    def test_request_kwargs(self, empty_context):
        app = SimpleMS()
        with app.app_context() as c:
            response = app(get_event('/kwparam1', 'get', params={'value': [5]}), empty_context)
            assert response['statusCode'] == 200
            assert response['body'] == "get **param with only 5"
            response = app(get_event('/kwparam1', 'get', params={"other": ['other'], "value": [5]}), empty_context)
            assert response['statusCode'] == 400
            response = app(get_event('/kwparam1', 'get', params={"value": [5]}), empty_context)
            assert response['statusCode'] == 200
            assert response['body'] == "get **param with only 5"
            response = app(get_event('/kwparam1', 'get', body={"other": 'other', "value": 5}), empty_context)
            assert response['statusCode'] == 200
            assert response['body'] == "get **param with only 0"
            response = app(get_event('/kwparam2', 'get', params={"other": ['other'], "value": [5]}), empty_context)
            assert response['statusCode'] == 200
            assert response['body'] == "get **param with 5 and ['other']"
            response = app(get_event('/kwparam2', 'get', body={"other": 'other', "value": 5}), empty_context)
            assert response['statusCode'] == 200
            assert response['body'] == "get **param with 0 and []"
            response = app(get_event('/kwparam2', 'put', body={"other": 'other', "value": 5}), empty_context)
            assert response['statusCode'] == 200
            assert response['body'] == "get **param with 5 and ['other']"
            response = app(get_event('/kwparam2', 'put', params={"other": ['other'], "value": [5]}), empty_context)
            assert response['statusCode'] == 200
            assert response['body'] == "get **param with 0 and []"
            response = app(get_event('/extended/content', 'get'), empty_context)
            assert response['statusCode'] == 200
            assert response['body'] == "hello world"

    def test_request_globals(self, empty_context):
        app = GlobalMS()
        with app.app_context() as c:
            response = app(get_event('/event/method', 'get'), empty_context)
            assert response['statusCode'] == 200
            assert response['body'] == "GET"

    def test_request_no_content_type(self, empty_context):
        app = SimpleMS()
        with app.app_context() as c:
            event = get_event('/content', 'post', body={"other": 'other'})
            del event['headers']['content-type']
            response = app(event, empty_context)
            assert response['statusCode'] == 200
            assert response['body'] == "post content without value but other"

    def test_request_error(self, empty_context):
        app = ErrorMS()
        with app.app_context() as c:
            event = get_event('/', 'get')
            response = app(event, empty_context)
            assert response['statusCode'] == 404
            assert response['body'] == "Error 404"
            event = get_event('/exception', 'get')
            response = app(event, empty_context)
            assert response['statusCode'] == 500
            app.err.assert_called_once()
