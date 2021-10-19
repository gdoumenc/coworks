from tests.coworks.ms import GlobalMS
from tests.coworks.ms import SimpleMS


def get_event(path, method, params=None, body=None):
    return {
        'type': 'LAMBDA',
        'resource': path,
        'path': path,
        'httpMethod': method.upper(),
        'headers': {
            'Accept': '*/*',
            'Authorization': 'token',
            'CloudFront-Forwarded-Proto': 'https',
            'CloudFront-Is-Desktop-Viewer': 'true',
            'CloudFront-Is-Mobile-Viewer': 'false',
            'CloudFront-Is-SmartTV-Viewer': 'false',
            'CloudFront-Is-Tablet-Viewer': 'false',
            'CloudFront-Viewer-Country': 'FR',
            'content-type': 'application/json',
            'Host': 'htzd2rneg1.execute-api.eu-west-1.amazonaws.com',
            'User-Agent': 'insomnia/2021.4.1',
            'Via': '2.0 4dd111c814b0b5cf8bf82e59008da625.cloudfront.net (CloudFront)',
            'X-Amz-Cf-Id': 'ka1hbQCSUOZ-d0VQYuE_gtF4icy443t7kP3UGsDLZDF_5QyTX13FoQ==',
            'X-Amzn-Trace-Id': 'Root=1-6124f604-3fb9457c7489ebf14ed0f8f6',
            'X-Forwarded-For': '78.234.174.193, 130.176.152.165',
            'X-Forwarded-Port': '443',
            'X-Forwarded-Proto': 'https'
        },
        'multiValueHeaders': {},
        'body': body or {},
        'queryStringParameters': {},
        'multiValueQueryStringParameters': params or {},
        'pathParameters': {},
        'stageVariables': None,
        'isBase64Encoded': False,
        'requestContext': {
            'httpMethod': 'GET',
            'resourceId': 'fp5ol74tr7',
            'resourcePath': '/',
            'extendedRequestId': 'EktgyFweDoEFabw=',
            'requestTime': '24/Aug/2021:13:37:08 +0000',
            'path': '/dev/',
            'accountId': '935392763270',
            'protocol': 'HTTP/1.1',
            'stage': 'dev',
            'domainPrefix': 'htzd2rneg1',
            'requestTimeEpoch': 1629812228818,
            'requestId': '2fa7f00a-58fe-4f46-a829-1fee00898e42',
            'domainName': 'htzd2rneg1.execute-api.eu-west-1.amazonaws.com',
            'apiId': 'htzd2rneg1'
        },
        'params': {
            'path': {},
            'querystring': {},
            'header': {'Accept': '*/*', 'Authorization': 'token', 'CloudFront-Forwarded-Proto': 'https',
                       'CloudFront-Is-Desktop-Viewer': 'true', 'CloudFront-Is-Mobile-Viewer': 'false',
                       'CloudFront-Is-SmartTV-Viewer': 'false', 'CloudFront-Is-Tablet-Viewer': 'false',
                       'CloudFront-Viewer-Country': 'FR', 'content-type': 'application/json',
                       'Host': 'htzd2rneg1.execute-api.eu-west-1.amazonaws.com', 'User-Agent': 'insomnia/2021.4.1',
                       'Via': '2.0 4dd111c814b0b5cf8bf82e59008da625.cloudfront.net (CloudFront)',
                       'X-Amz-Cf-Id': 'ka1hbQCSUOZ-d0VQYuE_gtF4icy443t7kP3UGsDLZDF_5QyTX13FoQ==',
                       'X-Amzn-Trace-Id': 'Root=1-6124f604-3fb9457c7489ebf14ed0f8f6',
                       'X-Forwarded-For': '78.234.174.193, 130.176.152.165', 'X-Forwarded-Port': '443',
                       'X-Forwarded-Proto': 'https'}},
        'context': {
            'resourceId': 'fp5ol74tr7',
            'authorizer': '',
            'resourcePath': '/',
            'httpMethod': 'GET',
            'extendedRequestId': 'EktgyFweDoEFabw=',
            'requestTime': '24/Aug/2021:13:37:08 +0000',
            'path': '/dev/',
            'accountId': '935392763270',
            'protocol': 'HTTP/1.1',
            'requestOverride': '',
            'stage': 'dev',
            'domainPrefix': 'htzd2rneg1',
            'requestTimeEpoch': '1629812228818',
            'requestId': '2fa7f00a-58fe-4f46-a829-1fee00898e42',
            'identity': '',
            'domainName': 'htzd2rneg1.execute-api.eu-west-1.amazonaws.com',
            'responseOverride': '',
            'apiId': 'htzd2rneg1'
        }
    }


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
