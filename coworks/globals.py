from functools import partial

from flask.globals import _lookup_req_object
from werkzeug.local import LocalProxy

aws_event = LocalProxy(partial(_lookup_req_object, "aws_event"))
aws_context = LocalProxy(partial(_lookup_req_object, "aws_context"))
