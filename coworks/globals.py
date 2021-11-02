import typing as t
from flask import request as flask_request
from flask.globals import _lookup_req_object
from functools import partial
from werkzeug.local import LocalProxy

if t.TYPE_CHECKING:
    from .wrappers import Request

aws_event = LocalProxy(partial(_lookup_req_object, "aws_event"))
aws_context = LocalProxy(partial(_lookup_req_object, "aws_context"))
request: "Request" = t.cast("Request", flask_request)
