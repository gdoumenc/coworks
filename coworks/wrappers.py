import typing as t

from flask import Request as FlaskRequest
from flask import Response as FlaskResponse
from werkzeug.datastructures import ETags


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
        self.aws_query_string = environ.get('aws_query_string') if self._in_lambda_context else None

        super().__init__(environ, **kwargs)

    @property
    def in_lambda_context(self):
        """Defined as a property to be read only."""
        return self._in_lambda_context

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
        return self.aws_query_string if self._in_lambda_context else super().args

    @property
    def if_match(self):  # No cache
        return ETags()

    @property
    def if_none_match(self):  # No cache
        return ETags()

    @property
    def if_modified_since(self):  # No cache
        return None
