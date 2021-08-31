from flask import Request as FlaskRequest
from flask import Response as FlaskResponse


class ApiResponse(FlaskResponse):
    """Default mimetype is redefined."""
    default_mimetype = "application/json"


class Request(FlaskRequest):

    def __init__(self, environ, **kwargs):
        super().__init__(environ, **kwargs)
        self.in_aws_lambda = 'aws_event' in environ
