import traceback

import typing as t
from aws_xray_sdk import global_sdk_config
from aws_xray_sdk.core import patch_all
from functools import partial, update_wrapper

from flask import make_response

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
        self._app.errorhandler(500)(self.capture_exception)
        self._recorder = recorder
        self._enabled = False

        def first():
            app.logger.debug(f"Initializing xray middleware {name}")

            # Checks XRay is enabled
            self._enabled = global_sdk_config.sdk_enabled()
            if self._enabled:
                try:
                    subsegment = self._recorder.current_subsegment()
                except (Exception,) as e:
                    self._app.logger.debug(str(e))
                    self._enabled = False

            if not self._enabled:
                self._app.logger.debug("Skipped capture routes because the SDK is currently disabled.")
                return

            patch_all()

        app.before_first_request_funcs = [first, *app.before_first_request_funcs]

    def capture_routes(self):
        if not self._enabled:
            return

        try:
            for rule in self._app.url_map.iter_rules():
                view_function = self._app.view_functions[rule.endpoint]

                def captured(_view_function, *args, **kwargs):

                    # Traces event, context, request and coworks function
                    subsegment = self._recorder.current_subsegment()
                    if subsegment:
                        try:
                            subsegment.put_metadata('context', lambda_context_to_json(aws_context),
                                                    LAMBDA_NAMESPACE)

                            metadata = {
                                'service': self._app.name,
                                'request': request_to_dict(request),
                            }
                            if request.is_json:
                                try:
                                    metadata['json'] = request.json
                                except (Exception,):
                                    metadata['json'] = request.get_data(cache=False, as_text=True)
                            elif request.is_multipart:
                                metadata['multipart'] = request.form.to_dict(False)
                                metadata['files'] = [*request.files.keys()]
                            elif request.is_form_urlencoded:
                                metadata['form'] = request.form.to_dict(False)
                                metadata['files'] = [*request.files.keys()]
                            else:
                                metadata['values'] = request.values.to_dict(False)
                            subsegment.put_metadata('request', metadata, COWORKS_NAMESPACE)
                        except (Exception,) as e:
                            self._app.logger.error(f"Cannot capture before route in XRay : {e}")
                            self._app.logger.error(traceback.extract_stack())

                    response = _view_function(*args, **kwargs)

                    # Traces response
                    if subsegment:
                        flask_response = make_response(response)
                        try:
                            metadata = {
                                'status': flask_response.status,
                                'headers': flask_response.headers,
                                'direct_passthrough': flask_response.direct_passthrough,
                                'is_json': flask_response.is_json,
                            }
                            subsegment.put_metadata('response', metadata, COWORKS_NAMESPACE)
                        except (Exception,) as e:
                            self._app.logger.error(f"Cannot capture after route in XRay : {e}")
                            self._app.logger.error(traceback.extract_stack())
                    return response

                wrapped_fun = update_wrapper(partial(captured, view_function), view_function)
                self._app.view_functions[rule.endpoint] = self._recorder.capture(name=wrapped_fun.__name__)(wrapped_fun)

        except Exception:
            self._app.logger.error("Cannot set xray context manager : are you using xray_recorder?")
            raise

    def capture_exception(self, e):
        if not self._enabled:
            self._app.logger.error(f"Event: {aws_event}")
            self._app.logger.error(f"Context: {aws_context}")
            self._app.logger.debug("Skipped capture exception because the SDK is currently disabled.")

        subsegment = self._recorder.current_subsegment()
        if subsegment:
            subsegment.add_error_flag()
            subsegment.put_annotation('service', self._app.name)
            subsegment.add_exception(e, traceback.extract_stack())

    @staticmethod
    def capture(recorder):
        """Decorator to trace function calls on XRay."""
        enabled = global_sdk_config.sdk_enabled()
        if not enabled:
            return lambda x: x

        # Set XRay decorator
        def xray_decorator(function):
            def xray_captured(*args, **kwargs):
                subsegment = recorder.current_subsegment()
                if subsegment:
                    try:
                        subsegment.put_metadata(f'{function.__name__}.args', args[1:], COWORKS_NAMESPACE)
                        subsegment.put_metadata(f'{function.__name__}.kwargs', kwargs, COWORKS_NAMESPACE)
                    except (Exception,) as e:
                        pass

                response = function(*args, **kwargs)
                if subsegment:
                    try:
                        subsegment.put_metadata(f'{function.__name__}.response', response, COWORKS_NAMESPACE)
                    except (Exception,) as e:
                        pass

                return response

            wrapped_fun = update_wrapper(xray_captured, function)
            return recorder.capture(name=function.__name__)(wrapped_fun)

        return xray_decorator


def lambda_context_to_json(context):
    return {
        'function_name': context.function_name,
        'function_version': context.function_version,
        'memory_limit_in_mb': context.memory_limit_in_mb,
        'aws_request_id': context.aws_request_id,
        'remaining_time': context.get_remaining_time_in_millis(),
    }


def request_to_dict(_request):
    return {
        'in_lambda_context': _request.in_lambda_context,
        'is_multipart': _request.is_multipart,
        'is_form_urlencoded': _request.is_form_urlencoded,
        'max_content_length': _request.max_content_length,
        'endpoint': _request.endpoint,
        'want_form_data_parsed': _request.want_form_data_parsed,
        'script_root': _request.script_root,
        'url_root': _request.url_root,
    }
