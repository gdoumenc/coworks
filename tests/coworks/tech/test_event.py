from unittest.mock import Mock

from flask import request, url_for
from werkzeug.exceptions import MethodNotAllowed, InternalServerError
from werkzeug.exceptions import NotFound
from werkzeug.exceptions import UnprocessableEntity

from coworks import TechMicroService
from coworks import entry
from ..event import get_event
from ..ms import GlobalMS
from ..ms import SimpleMS


class CookiesMS(TechMicroService):

    @entry
    def get_cookies(self):
        return request.cookies.to_dict()

    @entry
    def get_url_for(self, external=None):
        return url_for('get_cookies', _external=external)


class ErrorMS(TechMicroService):

    def __init__(self):
        super().__init__()
        self.err = Mock()

        @self.errorhandler(500)
        def handle(e):
            self.err(e)
            return "ok"

    @entry
    def get(self):
        """Root access."""
        return "Error 404", 404

    @entry
    def get_exception(self):
        """Root access."""
        return int("a")

    @entry
    def get_http_exception(self):
        """Root access."""
        raise InternalServerError()


class TestClass:
    def test_request_arg(self, empty_aws_context):
        app = SimpleMS()
        with app.app_context() as c:
            response = app(get_event('/', 'get'), empty_aws_context)
            assert response['statusCode'] == 200
            assert response['body'] == "get"
            assert 'Content-Type' in response['headers']
            assert response['headers']['Content-Type'] == 'text/plain; charset=utf-8'
            assert 'Content-Length' in response['headers']
            assert response['headers']['Content-Length'] == str(len(response['body']))
            response = app(get_event('/', 'post'), empty_aws_context)
            assert response['statusCode'] == MethodNotAllowed.code
            response = app(get_event('/get1', 'get'), empty_aws_context)
            assert response['statusCode'] == NotFound.code
            response = app(get_event('/content', 'get'), empty_aws_context)
            assert response['statusCode'] == 200
            assert response['body'] == "get content"
            response = app(
                get_event('/content/{value}', 'get', entry_path_parameters={'value': 3}),
                empty_aws_context)
            assert response['statusCode'] == 200
            assert response['body'] == "get content with 3"
            response = app(
                get_event('/content/{value}/{other}', 'get', entry_path_parameters={'value': 3, 'other': 'other'}),
                empty_aws_context)
            assert response['statusCode'] == 200
            assert response['body'] == "get content with 3 and other"
            response = app(
                get_event('/content', 'post', body={"other": 'other'}),
                empty_aws_context)
            assert response['statusCode'] == 200
            assert response['body'] == "post content without value but other"
            response = app(
                get_event('/content/{value}', 'post', entry_path_parameters={'value': 3}, body={"other": 'other'}),
                empty_aws_context)
            assert response['statusCode'] == 200
            assert response['body'] == "post content with 3 and other"
            response = app(get_event(
                '/content/{value}', 'post', entry_path_parameters={'value': 3}, body="other"),
                empty_aws_context)
            assert response['statusCode'] == 200
            assert response['body'] == "post content with 3 and other"
            response = app(
                get_event('/content/{value}', 'post', entry_path_parameters={'value': 3},
                          body={"other": 'other', "value": 5}),
                empty_aws_context)
            assert response['statusCode'] == UnprocessableEntity.code

    def test_request_kwargs(self, empty_aws_context):
        app = SimpleMS()
        with app.app_context() as c:
            response = app(get_event('/kwparam1', 'get', params={'value': [5]}), empty_aws_context)
            assert response['statusCode'] == 200
            assert response['body'] == "get **param with only 5"
            response = app(get_event('/kwparam1', 'get', params={"other": ['other'], "value": [5]}), empty_aws_context)
            assert response['statusCode'] == 422
            response = app(get_event('/kwparam1', 'get', params={"value": [5]}), empty_aws_context)
            assert response['statusCode'] == 200
            assert response['body'] == "get **param with only 5"
            response = app(get_event('/kwparam1', 'get', body={"other": 'other', "value": 5}), empty_aws_context)
            assert response['statusCode'] == 200
            assert response['body'] == "get **param with only 0"
            response = app(get_event('/kwparam2', 'get', params={"other": ['other'], "value": [5]}), empty_aws_context)
            assert response['statusCode'] == 200
            assert response['body'] == "get **param with 5 and ['other']"
            response = app(get_event('/kwparam2', 'get', body={"other": 'other', "value": 5}), empty_aws_context)
            assert response['statusCode'] == 200
            assert response['body'] == "get **param with 0 and []"
            response = app(get_event('/kwparam2', 'put', body={"other": 'other', "value": 5}), empty_aws_context)
            assert response['statusCode'] == 200
            assert response['body'] == "get **param with 5 and ['other']"
            response = app(get_event('/kwparam2', 'put', params={"other": ['other'], "value": [5]}), empty_aws_context)
            assert response['statusCode'] == 200
            assert response['body'] == "get **param with 0 and []"
            response = app(get_event('/extended/content', 'get'), empty_aws_context)
            assert response['statusCode'] == 200
            assert response['body'] == "hello world"

    def test_request_globals(self, empty_aws_context):
        app = GlobalMS()
        with app.app_context() as c:
            response = app(get_event('/event/method', 'get'), empty_aws_context)
            assert response['statusCode'] == 200
            assert response['body'] == "GET"

    def test_request_cookies(self, empty_aws_context):
        app = CookiesMS()
        with app.app_context() as c:
            response = app(get_event('/cookies', 'get'), empty_aws_context)
            assert response['statusCode'] == 200
            assert response['body'] == {'session': '70b58773-af3e-4153-a5ab-5356481ea87e'}

    def test_request_no_content_type(self, empty_aws_context):
        """If content-type is not defined then default is application/json"""
        app = SimpleMS()
        with app.app_context() as c:
            event = get_event('/content', 'post', body={'other': 'other'})
            del event['headers']['content-type']
            response = app(event, empty_aws_context)
            assert response['statusCode'] == 200
            assert response['body'] == "post content without value but other"

    def test_request_error(self, empty_aws_context):
        app = ErrorMS()
        with app.app_context() as c:
            event = get_event('/', 'get')
            response = app(event, empty_aws_context)
            assert response['statusCode'] == NotFound.code
            assert response['body'] == "Error 404"
            event = get_event('/exception', 'get')
            response = app(event, empty_aws_context)
            assert response['statusCode'] == 500
            app.err.assert_not_called()
            event = get_event('/http/exception', 'get')
            response = app(event, empty_aws_context)
            assert response['statusCode'] == 200
            app.err.assert_called_once()

    def test_url_for(self, empty_aws_context):
        app = CookiesMS()
        with app.app_context() as c:
            event = get_event('/url/for', 'get')
            response = app(event, empty_aws_context)
            assert response['statusCode'] == 200
            assert response['body'] == '/dev/cookies'
            event = get_event('/url/for', 'get', params={'external': True})
            response = app(event, empty_aws_context)
            assert response['statusCode'] == 200
            assert response['body'] == 'https://htzd2rneg1.execute-api.eu-west-1.amazonaws.com/dev/cookies'
            event = get_event('/url/for', 'get', params={'external': False})
            response = app(event, empty_aws_context)
            assert response['statusCode'] == 200
            assert response['body'] == '/dev/cookies'
