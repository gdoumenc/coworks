import typing as t
from functools import partial

from flask import request as flask_request
from flask.globals import _lookup_req_object
from werkzeug.local import LocalProxy

from .wrappers import CoworksRequest

aws_event = LocalProxy(partial(_lookup_req_object, "aws_event"))
aws_context = LocalProxy(partial(_lookup_req_object, "aws_context"))
request: "CoworksRequest" = t.cast("CoworksRequest", flask_request)
