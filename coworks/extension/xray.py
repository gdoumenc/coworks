import os
import typing as t
from aws_xray_sdk import global_sdk_config
from aws_xray_sdk.core.exceptions.exceptions import SegmentNotFoundException
from aws_xray_sdk.core.recorder import TRACING_NAME_KEY
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware
from functools import update_wrapper

if t.TYPE_CHECKING:
    from coworks import TechMicroService
    from aws_xray_sdk.core import AWSXRayRecorder

LAMBDA_NAMESPACE = 'lambda'
REQUEST_NAMESPACE = 'flask'
COWORKS_NAMESPACE = 'coworks'


class XRay:
    def __init__(self, app: "TechMicroService", recorder: "AWSXRayRecorder", name="xray"):
        self._app = app
        self._recorder = recorder
        self._name = name

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        if os.getenv(TRACING_NAME_KEY):
            XRayMiddleware(app, self._recorder)
        else:
            msg = f"Flask XRayMiddleware not installed because environment variable {TRACING_NAME_KEY} not defined."
            app.logger.info(msg)

    @staticmethod
    def capture(recorder):
        # Decorator to trace function calls on XRay.
        def xray_decorator(function):
            def function_captured(*args, **kwargs):
                subsegment = recorder.current_subsegment()
                if subsegment:
                    call_data = {
                        'args': args[1:],
                        'kwargs': kwargs,
                    }
                    subsegment.put_metadata(function.__name__, call_data, COWORKS_NAMESPACE)

                response = function(*args, **kwargs)

                if subsegment:
                    subsegment.put_metadata(f'{function.__name__}.response', response, COWORKS_NAMESPACE)

                return response

            if global_sdk_config.sdk_enabled():
                # Checks XRay is available
                try:
                    segment = recorder.current_segment()
                except SegmentNotFoundException as e:
                    pass
                else:
                    # Captures function
                    wrapped_fun = update_wrapper(function_captured, function)
                    return recorder.capture(name=function.__name__)(wrapped_fun)

            return function

        return xray_decorator
