import base64
import io
import json
import typing as t

from flask import Request as FlaskRequest
from flask import Response as FlaskResponse
from flask import current_app
from werkzeug.datastructures import ETags
from werkzeug.datastructures import Headers
from werkzeug.exceptions import HTTPException, BadRequest
from werkzeug.exceptions import MethodNotAllowed
from werkzeug.exceptions import NotFound
from werkzeug.routing import MapAdapter


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


class CoworksMapAdapter(MapAdapter):

    def __init__(self, environ, url_map, aws_url_map, stage_prefixed):
        server_name = environ["SERVER_NAME"]
        aws_stage = environ["aws_stage"]
        url_scheme = environ["REQUEST_SCHEME"]
        path_info = environ["PATH_INFO"]
        method = environ["REQUEST_METHOD"]
        script_name = f'/{aws_stage}/' if stage_prefixed else ''
        super().__init__(url_map, server_name=server_name, script_name=script_name, subdomain='',
                         url_scheme=url_scheme, path_info=path_info, default_method=method)
        self.aws_url_map = aws_url_map
        self.aws_entry_path = environ["aws_entry_path"]
        self.aws_entry_path_parameters = environ["aws_entry_path_parameters"]

    def match(self, method=None, return_rule=False, **kwargs):
        try:
            if self.aws_entry_path not in self.aws_url_map:
                raise NotFound()

            rules = self.aws_url_map[self.aws_entry_path]
            for rule in rules:
                if self.default_method in rule.methods:
                    return rule if return_rule else rule.endpoint, self.aws_entry_path_parameters
            else:
                raise MethodNotAllowed()
        except HTTPException:
            raise
        except Exception as e:
            current_app.logger.debug(f"Rule match error {e}")
            raise NotFound()


class CoworksResponse(FlaskResponse):
    """Default mimetype is redefined."""
    default_mimetype = "application/json"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


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
        if not self.in_lambda_context:
            return super().args
        return self.aws_query_string

    @property
    def stream(self):
        if not self.in_lambda_context:
            return super().stream

        print(self.is_multipart)
        print(self.is_form_urlencoded)

        if self.is_multipart:
            return io.BytesIO(base64.b64decode(self.aws_body))
        if self.is_form_urlencoded:
            return io.BytesIO(self.aws_body.encode('ascii'))
        raise BadRequest(f'Undefined mime-type: {self.mimetype}')

    @property
    def form(self):
        if not self.in_lambda_context:
            return super().form

        parser = self.make_form_data_parser()
        data = parser.parse(
            self.stream,
            self.mimetype,
            self.content_length,
            self.mimetype_params,
        )
        d = self.__dict__
        d["stream"], d["form"], d["files"] = data
        return d["form"]

    def get_data(self, **kwargs):
        if not self.in_lambda_context:
            return super().get_data(**kwargs)
        return json.dumps(self.aws_body) if kwargs.get('as_text', False) else self.aws_body

    def get_json(self, **kwargs):
        if not self.in_lambda_context:
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
