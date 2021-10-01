import traceback
import typing as t
from functools import partial, update_wrapper

from aws_xray_sdk.core import patch_all

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
                            try:
                                subsegment.put_annotation('service', self._app.name)
                                subsegment.put_metadata('event', aws_event, LAMBDA_NAMESPACE)
                                subsegment.put_metadata('context', lambda_context_to_json(aws_context),
                                                        LAMBDA_NAMESPACE)
                                subsegment.put_metadata('request', request_to_dict(request), REQUEST_NAMESPACE)
                                if request.is_json:
                                    subsegment.put_metadata('json', request.json, COWORKS_NAMESPACE)
                                elif request.is_multipart:
                                    subsegment.put_metadata('multipart', request.form.to_dict(False), COWORKS_NAMESPACE)
                                elif request.is_form_urlencoded:
                                    subsegment.put_metadata('form', request.form.to_dict(False), COWORKS_NAMESPACE)
                                else:
                                    subsegment.put_metadata('values', request.values.to_dict(False), COWORKS_NAMESPACE)
                            except Exception as e:
                                self._app.logger.info(f"Cannot capture in XRay : {e}")

                        response = _view_function(*args, **kwargs)

                        # Traces response
                        if subsegment:
                            try:
                                subsegment.put_metadata('status', response.status, COWORKS_NAMESPACE)
                                subsegment.put_metadata('headers', response.headers, COWORKS_NAMESPACE)
                                subsegment.put_metadata('direct_passthrough', response.direct_passthrough,
                                                        COWORKS_NAMESPACE)
                                subsegment.put_metadata('is_json', response.is_json, COWORKS_NAMESPACE)
                                subsegment.put_metadata('content_length', response.content_length, COWORKS_NAMESPACE)
                                subsegment.put_metadata('content_type', response.content_type, COWORKS_NAMESPACE)
                            except Exception as e:
                                self._app.logger.info(f"Cannot capture in XRay : {e}")
                        return response

                    wrapped_fun = update_wrapper(partial(captured, view_function), view_function)
                    self._app.view_functions[rule.endpoint] = self._recorder.capture(view_function.__name__)(
                        wrapped_fun)

        except Exception:
            self._app.logger.error("Cannot set xray context manager : are you using xray_recorder?")
            raise

    def capture_exception(self, e):

        # Only available in lambda context
        if not request.in_lambda_context:
            raise e

        try:
            self._app.logger.error(f"Event: {aws_event}")
            self._app.logger.error(f"Context: {aws_context}")
            subsegment = self._recorder.current_subsegment()
            if subsegment:
                subsegment.add_error_flag()
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


def lambda_context_to_json(context):
    return {
        'function_name': context.function_name,
        'function_version': context.function_version,
        'memory_limit_in_mb': context.memory_limit_in_mb,
        'aws_request_id': context.aws_request_id,
        'remaining_time': context.get_remaining_time_in_millis(),
    }


def request_to_dict(request):
    return {
        'in_lambda_context': request.in_lambda_context,
        'is_multipart': request.is_multipart,
        'is_form_urlencoded': request.is_form_urlencoded,
        'max_content_length': request.max_content_length,
        'endpoint': request.endpoint,
        'want_form_data_parsed': request.want_form_data_parsed,
        'data': request.data,
        'form': request.form,
        'json': request.json,
        'values': request.values,
        'script_root': request.script_root,
        'url_root': request.url_root,
    }
