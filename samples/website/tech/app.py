# from aws_xray_sdk.core import xray_recorder
# from coworks.extension.xray import XRay
from flask import json
from werkzeug.datastructures import MultiDict

from config import DevConfig
from config import LocalConfig
from config import ProdConfig
from website import WebsiteMicroService

local = LocalConfig()
test = DevConfig('test')
dev = DevConfig()
prod = ProdConfig()

app = WebsiteMicroService(configs=[local, test, dev, prod])

from coworks.wrappers import CoworksRequest


class Request(CoworksRequest):

    def __init__(self, environ, **kwargs):
        self.aws_event = environ.pop('aws_event', None)
        self.aws_context = environ.pop('aws_context', None)
        self._in_lambda_context: bool = self.aws_event is not None
        if self._in_lambda_context:
            request_context = self.aws_event['requestContext']
            stage = request_context.get('stage')
            path = request_context.get('path')[len(stage) + 1:]
            lambda_environ = {
                'CONTENT_TYPE': 'application/json',
                'CONTENT_LENGTH': environ.get('CONTENT_LENGTH', 0),
                'REQUEST_METHOD': self.aws_event.get('httpMethod'),
                'PATH_INFO': path,
                'HTTP_HOST': request_context.get('host'),
                'SCRIPT_NAME': f"/{stage}/",
                'SERVER_NAME': request_context.get('domainName'),
                'SERVER_PROTOCOL': 'http',
                'SERVER_PORT': '80',
                'wsgi.url_scheme': 'http',
                # 'RAW_URI': self.aws_event.get('path'),
                # 'REQUEST_URI': self.aws_event.get('path'),
            }
            for k, value in self.aws_event['headers'].items():
                if k.startswith('HTTP_') or k.startswith('X_'):
                    key = k
                elif k.startswith('x_'):
                    key = k.upper()
                else:
                    key = f'HTTP_{k.upper()}'
                lambda_environ[key] = value

            self.query_params = MultiDict(self.aws_event['multiValueQueryStringParameters'])
            self.body = json.dumps(self.aws_event['body'])

            print(lambda_environ)
            super().__init__(lambda_environ, **kwargs)
        else:
            super().__init__(environ, **kwargs)


app.request_class = Request
