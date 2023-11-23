from flask import make_response
from jsonapi_pydantic.v1_0 import Error
from jsonapi_pydantic.v1_0 import TopLevel
from pydantic import ValidationError
from werkzeug.exceptions import BadRequest
from werkzeug.exceptions import HTTPException
from werkzeug.exceptions import InternalServerError

from coworks.globals import request


class JsonApiError(Exception):

    def __init__(self, id, title, detail=None):
        self.error = Error(id=id, code=id, title=title, detail=detail, status=InternalServerError.code)


class JsonApi:
    """Flask's extension implementing JSON:API specification.
    This extension uses the external API of ODOO.

    .. versionchanged:: 0.7.3
        ``env_var_prefix`` parameter may be a dict of bind values.
        GraphQL removed.
    """

    def __init__(self, app=None):
        """
        :param app: Flask application.
        """
        self.app = None

        if app:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        handle_user_exception = app.handle_user_exception

        def _handle_user_exception(e):
            if 'application/vnd.api+json' not in request.headers.getlist('accept'):
                return handle_user_exception(e)

            if isinstance(e, ValidationError):
                errors = [Error(id=BadRequest.code, status=BadRequest.code,
                                title=str(err.exc), detail=str(err)) for err in e.raw_errors]
                return self._top_level_error_response(errors, BadRequest.code)

            try:
                rv = handle_user_exception(e)
                if isinstance(rv, HTTPException):
                    errors = [Error(id='0', title=rv.name, detail=rv.description, status=rv.code)]
                    return self._top_level_error_response(errors, rv.code)
            except (Exception,):
                pass

            if isinstance(e, JsonApiError):
                errors = [e.error]
            else:
                errors = [Error(id='0', title=e.__class__.__name__, detail=str(e), status=InternalServerError.code)]
            return self._top_level_error_response(errors, InternalServerError.code)

        app.handle_user_exception = _handle_user_exception

        app.after_request(self._change_content_type)

    def _change_content_type(self, response):
        if 'application/vnd.api+json' not in request.headers.getlist('accept'):
            return response

        response.content_type = 'application/vnd.api+json'
        return response

    def _top_level_error_response(self, errors, status_code):
        top_level = TopLevel(data=None, errors=errors, included=None).dict()
        return make_response(top_level, status_code)
