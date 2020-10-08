from functools import partial, update_wrapper

from aws_xray_sdk.core.models import http

LAMBDA_NAMESPACE = 'lambda'
COWORKS_NAMESPACE = 'coworks'


class XRayMiddleware(object):

    def __init__(self, app, recorder):
        self.app = app
        self.app.logger.info("initializing xray middleware")

        self._recorder = recorder

        @app.before_first_activation
        def capture_routes(event, context):
            for path, route in app.routes.items():
                for method, entry in route.items():
                    view_function = entry.view_function
                    cws_function = view_function.__cws_func__

                    def captured(_view_function, *args, **kwargs):
                        subsegment = self._recorder.current_subsegment()
                        subsegment.put_metadata('event', event, LAMBDA_NAMESPACE)
                        subsegment.put_metadata('context', context, LAMBDA_NAMESPACE)
                        subsegment.put_annotation('service', app.name)
                        subsegment.put_metadata('query_params', app.current_request.query_params, COWORKS_NAMESPACE)
                        subsegment.put_metadata('json_body', app.current_request.json_body, COWORKS_NAMESPACE)
                        response = _view_function(*args, **kwargs)
                        subsegment.put_metadata('response', response, COWORKS_NAMESPACE)
                        return response

                    def captured_entry(_cws_function, *args, **kwargs):
                        subsegment = self._recorder.current_subsegment()
                        subsegment.put_metadata('args', args, COWORKS_NAMESPACE)
                        subsegment.put_metadata('kwargs', kwargs, COWORKS_NAMESPACE)
                        response = _cws_function(*args, **kwargs)
                        subsegment.put_metadata('response', response, COWORKS_NAMESPACE)
                        return response

                    wrapped_fun = update_wrapper(partial(captured, view_function), view_function)
                    entry.view_function = self._recorder.capture(view_function.__name__)(wrapped_fun)

                    wrapped_fun = update_wrapper(partial(captured_entry, cws_function), cws_function)
                    entry.view_function.__cws_func__ = self._recorder.capture(cws_function.__name__)(wrapped_fun)
