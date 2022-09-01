import typing as t

from flask import request as flask_request

from .wrappers import CoworksRequest

request: "CoworksRequest" = t.cast("CoworksRequest", flask_request)
