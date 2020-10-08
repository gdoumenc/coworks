from unittest.mock import Mock

import requests

from coworks.middleware.xray_middleware import XRayMiddleware
from tests.src.coworks.tech_ms import *


def const_id(*args):
    return lambda x: x


xray_recorder = Mock()
segment = Mock()
xray_recorder.capture = Mock(side_effect=const_id)
xray_recorder.current_subsegment = Mock(return_value=segment)


class TestMiddleware:
    def __init__(self, app):
        app.before_first_activation(self.always_first)
        app.before_activation(self.before)
        app.after_activation(self.at_least)
        app.handle_exception(self.on_exception)
        self.evts = []

    def always_first(self, event, context):
        self.evts.append("first")

    def before(self, event, context):
        self.evts.append("before")

    def at_least(self, response):
        if response['statusCode'] == 400:
            self.evts.append("error")
        else:
            self.evts.append("after")
        return response

    def on_exception(self, exc):
        self.evts.append("exception")


class TestClass:

    def test_decorators(self, local_server_factory):
        simple = SimpleMS()
        evts = []

        @simple.before_first_activation
        def always_first(event, context):
            evts.append("first")

        @simple.before_activation
        def before(event, context):
            evts.append("before")

        @simple.after_activation
        def at_least(response):
            if response['statusCode'] == 400:
                evts.append("error")
            else:
                evts.append("after")
            return response

        @simple.handle_exception
        def on_exception(exc):
            evts.append("exception")

        local_server = local_server_factory(simple)
        local_server.make_call(requests.get, '/')
        local_server.make_call(requests.get, '/')
        assert evts == ["first", "before", "after", "before", "after"]

    def test_middleware(self, local_server_factory):
        simple = SimpleMS()
        middleware = TestMiddleware(simple)
        local_server = local_server_factory(simple)
        response = local_server.make_call(requests.get, '/')
        assert response.status_code == 200
        assert response.text == 'get'
        assert middleware.evts == ["first", "before", "after"]
        response = local_server.make_call(requests.get, '/')
        assert response.status_code == 200
        assert middleware.evts == ["first", "before", "after", "before", "after"]
        response = local_server.make_call(requests.get, '/?wrong=1')
        assert response.status_code == 400
        assert 'error' in middleware.evts

    def test_xray_middleware(self, local_server_factory):
        simple = SimpleMS()
        XRayMiddleware(simple, xray_recorder)
        local_server = local_server_factory(simple)
        response = local_server.make_call(requests.get, '/')
        assert response.status_code == 200
        assert response.text == 'get'
        xray_recorder.capture.assert_called()
        segment.put_annotation.assert_called()
