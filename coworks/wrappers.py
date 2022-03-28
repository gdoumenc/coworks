import typing as t

from flask import Request as FlaskRequest
from flask import Response as FlaskResponse


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
        super().__init__(environ, **kwargs)
        aws_event = environ.get('aws_event')
        self._in_lambda_context: bool = bool(aws_event)
        if self._in_lambda_context:
            environ['wsgi.url_scheme'] = aws_event['headers'].get('x-forwarded-proto')
            environ['HTTP_REFERER'] = aws_event['headers'].get('referer')
            environ['HTTP_HOST'] = aws_event['headers'].get('x-forwarded-host')

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
