import traceback
from functools import partial, update_wrapper

LAMBDA_NAMESPACE = 'lambda'
COWORKS_NAMESPACE = 'coworks'


class XRayContextManager:

    def __init__(self, app, recorder):
        app.logger.info("initializing xray middleware")

        @app.before_first_activation
        def capture_routes(event, context):
            for path, route in app.routes.items():
                for method, entry in route.items():
                    view_function = entry.view_function
                    cws_function = view_function.__cws_func__

                    def captured(_view_function, *args, **kwargs):
                        subsegment = recorder.current_subsegment()
                        if subsegment:
                            subsegment.put_metadata('event', event, LAMBDA_NAMESPACE)
                            subsegment.put_metadata('context', context, LAMBDA_NAMESPACE)
                            subsegment.put_annotation('service', app.name)
                            subsegment.put_metadata('query_params', app.current_request.query_params, COWORKS_NAMESPACE)
                            if app.current_request.raw_body:
                                subsegment.put_metadata('json_body', app.current_request.json_body, COWORKS_NAMESPACE)
                        response = _view_function(*args, **kwargs)
                        if subsegment:
                            subsegment.put_metadata('response', response, COWORKS_NAMESPACE)
                        return response

                    def captured_entry(_cws_function, *args, **kwargs):
                        subsegment = recorder.current_subsegment()
                        if subsegment:
                            subsegment.put_metadata('args', args, COWORKS_NAMESPACE)
                            subsegment.put_metadata('kwargs', kwargs, COWORKS_NAMESPACE)
                        response = _cws_function(*args, **kwargs)
                        if subsegment:
                            subsegment.put_metadata('response', response, COWORKS_NAMESPACE)
                        return response

                    wrapped_fun = update_wrapper(partial(captured, view_function), view_function)
                    entry.view_function = recorder.capture(view_function.__name__)(wrapped_fun)

                    wrapped_fun = update_wrapper(partial(captured_entry, cws_function), cws_function)
                    entry.view_function.__cws_func__ = recorder.capture(cws_function.__name__)(wrapped_fun)

        @app.handle_exception
        def capture_exception(event, context, e):
            try:
                app.logger.error(f"Event: {event}")
                app.logger.error(f"Context: {context}")
                app.logger.error(f"Exception: {str(e)}")
                app.logger.error(traceback.print_exc())
                subsegment = recorder.current_subsegment
                if subsegment:
                    subsegment.put_annotation('service', app.name)
                    subsegment.add_exception(e, traceback.extract_stack())
            except Exception:
                return {
                    'headers': {},
                    'multiValueHeaders': {},
                    'statusCode': 500,
                    'body': "Exception in microservice, see logs in XRay"
                }
