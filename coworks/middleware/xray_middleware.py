from functools import partial, update_wrapper

from aws_xray_sdk.core.models import http

COWORKS_NAMESPACE = 'coworks'


class XRayMiddleware(object):

    def __init__(self, app, recorder):
        self.app = app
        self.app.logger.info("initializing xray middleware")

        self._recorder = recorder

        @self.app.before_first_activation
        def capture_routes(event, context):
            for path, route in self.app.routes.items():
                for method, entry in route.items():
                    view_function = entry.view_function
                    cws_function = view_function.__cws_func__

                    def captured(_view_function, *args, **kwargs):
                        subsegment = self._recorder.current_subsegment()
                        subsegment.put_metadata('event', event, COWORKS_NAMESPACE)
                        subsegment.put_metadata('context', context, COWORKS_NAMESPACE)
                        subsegment.put_annotation('service', self.app.name)
                        subsegment.put_metadata('args', args, COWORKS_NAMESPACE)
                        subsegment.put_metadata('kwargs', kwargs, COWORKS_NAMESPACE)
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
