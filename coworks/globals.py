from functools import partial

from flask.globals import _lookup_req_object
from werkzeug.local import LocalProxy

event = LocalProxy(partial(_lookup_req_object, "event"))
context = LocalProxy(partial(_lookup_req_object, "context"))
