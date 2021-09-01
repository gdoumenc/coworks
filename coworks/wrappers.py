from flask import Request as FlaskRequest
from flask import Response as FlaskResponse


class ApiResponse(FlaskResponse):
    """Default mimetype is redefined."""
    default_mimetype = "application/json"


class Request(FlaskRequest):

    def __init__(self, environ, **kwargs):
        super().__init__(environ, **kwargs)
        self._in_lambda_context = 'aws_event' in environ

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
