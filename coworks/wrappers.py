import typing as t

from flask import Request as FlaskRequest
from flask import Response as FlaskResponse
from flask import json
from werkzeug.datastructures import MultiDict


class TokenResponse:
    """AWS authorization response."""

    def __init__(self, allow: bool, arn: str):
        """Value may be string when allowed only if match workspace label."""
        self.allow = allow
        self.arn = arn

    @property
    def json(self) -> t.Optional[t.Any]:
        return {
            "principalId": "user",
            "policyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": "execute-api:Invoke",
                        "Effect": "Allow" if self.allow else "Deny",
                        "Resource": self.arn
                    }
                ]
            }
        }


class CoworksResponse(FlaskResponse):
    """Default mimetype is redefined."""
    default_mimetype = "application/json"


class CoworksRequest(FlaskRequest):

    def __init__(self, environ, **kwargs):
        self.aws_event = environ.pop('aws_event', None)
        self.aws_context = environ.pop('aws_context', None)
        self._in_lambda_context: bool = self.aws_event is not None
        if self._in_lambda_context:
            request_context = self.aws_event['requestContext']
            lambda_environ = {
                'CONTENT_TYPE': 'application/json',
                'CONTENT_LENGTH': environ.get('CONTENT_LENGTH', 0),
                'REQUEST_METHOD': self.aws_event.get('httpMethod'),
                'PATH_INFO': self.aws_event.get('path'),
                'HTTP_HOST': request_context.get('host'),
                'SCRIPT_NAME': f"/{request_context.get('stage')}/",
                'SERVER_NAME': request_context.get('domainName'),
                'SERVER_PROTOCOL': 'http',
                'SERVER_PORT': '80',
                'wsgi.url_scheme': 'http',
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

            super().__init__(lambda_environ, **kwargs)
        else:
            super().__init__(environ, **kwargs)

    @property
    def in_lambda_context(self):
        """Defined as a property to be read only."""
        return self._in_lambda_context

    @property
    def values(self):
        return self.query_params if self._in_lambda_context else super().values

    def get_data(self, cache=True, as_text=False, parse_form_data=False):
        # noinspection PyTypeChecker
        return self.body if self._in_lambda_context else super().get_data(cache=cache, as_text=as_text,
                                                                          parse_form_data=parse_form_data)

    @property
    def is_multipart(self) -> bool:
        """Check if the mimetype indicates form-data.
        """
        mt = self.mimetype
        return (
                mt == "multipart/form-data"
        )

    @property
    def is_form_urlencoded(self) -> bool:
        """Check if the mimetype indicates form-data.
        """
        mt = self.mimetype
        return (
                mt == "application/x-www-form-urlencoded"
        )
