import json
import typing as t

from flask import Request as FlaskRequest
from flask import Response as FlaskResponse
from werkzeug.datastructures import ETags, Headers


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
        self.aws_event = environ.get('aws_event')
        self.aws_context = environ.get('aws_context')
        self.aws_query_string = environ.get('aws_query_string')
        self.aws_body = environ.get('aws_body')
        self._in_lambda_context: bool = self.aws_event is not None

        super().__init__(environ, **kwargs)

        if self._in_lambda_context:
            self.headers = Headers(self.aws_event.get('headers'))

    @property
    def in_lambda_context(self):
        """Defined as a property to be read only."""
        return self._in_lambda_context

    @property
    def is_json(self) -> bool:
        """If no content type defined in request, default is application/json`.        """
        return not self.mimetype or super().is_json

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

    @property
    def args(self):
        if self.aws_query_string is None:
            return super().args
        return self.aws_query_string

    def get_data(self, **kwargs):
        if self.aws_body is None:
            return super().get_data(**kwargs)
        return json.dumps(self.aws_body) if kwargs.get('as_text', False) else self.aws_body

    def get_json(self, **kwargs):
        if self.aws_body is None:
            return super().get_json(**kwargs)
        return self.aws_body

    @property
    def if_match(self):  # No cache
        return ETags()

    @property
    def if_none_match(self):  # No cache
        return ETags()

    @property
    def if_modified_since(self):  # No cache
        return None
