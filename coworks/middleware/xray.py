import traceback

import typing as t
from aws_xray_sdk.core import patch_all
from functools import partial, update_wrapper

from coworks.globals import aws_context
from coworks.globals import aws_event
from coworks.globals import request

if t.TYPE_CHECKING:
    from coworks import TechMicroService
    from aws_xray_sdk.core import AWSXRayRecorder

MIDDLEWARE_NAME = 'xray'
LAMBDA_NAMESPACE = 'lambda'
REQUEST_NAMESPACE = 'flask'
COWORKS_NAMESPACE = 'coworks'


class XRayMiddleware:

    def __init__(self, app: "TechMicroService", recorder: "AWSXRayRecorder", name=MIDDLEWARE_NAME):
        self._app = app
        self._app.before_first_request(self.capture_routes)
        self._app.handle_exception = self.capture_exception
        self._recorder = recorder
        app.logger.debug(f"Initializing xray middleware {name}")

    def capture_routes(self):

        # Only available in lambda context
        if not request.in_lambda_context:
            return

        try:
            patch_all()

            for rule in self._app.url_map.iter_rules():
                for http_method in rule.methods:
                    view_function = self._app.view_functions[rule.endpoint]

                    def captured(_view_function, *args, **kwargs):

                        # Traces event, context, request and coworks function
                        subsegment = self._recorder.current_subsegment()
                        if subsegment:
                            subsegment.put_annotation('service', self._app.name)
                            subsegment.put_metadata('event', aws_event, LAMBDA_NAMESPACE)
                            subsegment.put_metadata('context', aws_context, LAMBDA_NAMESPACE)
                            subsegment.put_metadata('request', request, REQUEST_NAMESPACE)
                            if request.is_json:
                                subsegment.put_metadata('json', request.json, COWORKS_NAMESPACE)
                            elif request.is_multipart:
                                subsegment.put_metadata('multipart', request.form.to_dict(False), COWORKS_NAMESPACE)
                            elif request.is_form_urlencoded:
                                subsegment.put_metadata('form', request.form.to_dict(False), COWORKS_NAMESPACE)
                            else:
                                subsegment.put_metadata('values', request.values.to_dict(False), COWORKS_NAMESPACE)

                        response = _view_function(*args, **kwargs)

                        # Traces response
                        if subsegment:
                            subsegment.put_metadata('response', response, COWORKS_NAMESPACE)
                        return response

                    wrapped_fun = update_wrapper(partial(captured, view_function), view_function)
                    self._app.view_functions[rule.endpoint] = self._recorder.capture(view_function.__name__)(
                        wrapped_fun)

        except Exception:
            self._app.logger.error("Cannot set xray context manager : are you using xray_recorder?")
            raise

    def capture_exception(self, e):
        self._app.logger.error(f"Exception: {str(e)}")
        self._app.logger.error(traceback.print_exc())

        # Only available in lambda context
        if not request.in_lambda_context:
            return

        try:
            self._app.logger.error(f"Event: {aws_event}")
            self._app.logger.error(f"Context: {aws_context}")
            subsegment = self._recorder.current_subsegment()
            if subsegment:
                subsegment.put_annotation('service', self._app.name)
                subsegment.add_exception(e, traceback.extract_stack())
        finally:
            return {
                'headers': {},
                'multiValueHeaders': {},
                'statusCode': 500,
                'body': "Exception in microservice, see logs in XRay for more details",
                'error': str(e)
            }

    @staticmethod
    def capture(recorder):
        """Decorator to trace function calls on XRay."""

        if not issubclass(recorder.__class__, AWSXRayRecorder):
            raise TypeError(f"recorder is not an AWSXRayRecorder {type(recorder)}")

        def decorator(function):
            def captured(*args, **kwargs):
                subsegment = recorder.current_subsegment()
                if subsegment:
                    subsegment.put_metadata(f'{function.__name__}.args', args, COWORKS_NAMESPACE)
                    subsegment.put_metadata(f'{function.__name__}.kwargs', kwargs, COWORKS_NAMESPACE)
                response = function(*args, **kwargs)
                if subsegment:
                    subsegment.put_metadata(f'{function.__name__}.response', response, COWORKS_NAMESPACE)
                return response

            wrapped_fun = update_wrapper(captured, function)
            return recorder.capture(function.__name__)(wrapped_fun)

        return decorator
