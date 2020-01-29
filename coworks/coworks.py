import inspect
import json
import logging
import os
import sys
import traceback
from functools import update_wrapper

from aws_xray_sdk.core import xray_recorder
from chalice import AuthResponse, BadRequestError, Rate, Cron
from chalice import Chalice, Blueprint as ChaliceBlueprint

from .mixins import Boto3Mixin
from .utils import class_auth_methods, class_rest_methods, class_attribute

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class TechMicroService(Chalice):
    """Simple chalice app created directly from class."""

    def __init__(self, **kwargs):
        app_name = kwargs.pop('app_name', self.__class__.__name__)
        super().__init__(app_name, **kwargs)
        self.experimental_feature_flags.update([
            'BLUEPRINTS'
        ])

        self.__auth__ = None
        self.blueprints = {}

        self._add_route()

        if "pytest" in sys.modules:
            xray_recorder.configure(context_missing="LOG_ERROR")

    def _initialize(self, env):
        super()._initialize(env)
        for k, v in env.items():
            os.environ[k] = v

    @property
    def component_name(self):
        return class_attribute(self, 'url_prefix', '')

    def register_blueprint(self, blueprint, **kwargs):
        self._add_route(blueprint)
        if 'name_prefix' not in kwargs:
            kwargs['name_prefix'] = blueprint.component_name
        if 'url_prefix' not in kwargs:
            kwargs['url_prefix'] = f"/{blueprint.component_name}"

        super().register_blueprint(blueprint, **kwargs)
        self.blueprints[blueprint.import_name] = blueprint

    def run(self, host='127.0.0.1', port=8000, stage=None, debug=True, profile=None, project_dir='.'):
        # TODO missing test
        # chalice.cli package not defined in deployment package
        from chalice.cli import DEFAULT_STAGE_NAME
        from .cli.factory import CWSFactory

        logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')

        stage = stage or DEFAULT_STAGE_NAME
        factory = CWSFactory(self, project_dir, debug, profile)
        config = factory.create_config_obj(chalice_stage_name=stage)
        factory.run_local_server(config, host, port)

    def _add_route(self, component=None):
        if component is None:
            component = self

            # Adds class authorizer for every entries
            auth = class_auth_methods(component)
            if auth:
                auth = TechMicroService._create_auth_proxy(component, auth)
                component.__auth__ = auth
        else:
            # Add the current_app auth
            auth = self.__auth__

        # Adds entrypoints
        methods = class_rest_methods(component)
        for method, func in methods:
            if func.__name__ == method:
                route = f"{component.component_name}"
            else:
                name = func.__name__[len(method) + 1:]
                while name.endswith('_'):
                    # to allow several functions with same route but different args
                    name = name[:-1]
                name = name.replace('_', '/')
                route = f"{component.component_name}/{name}" if component.component_name else f"{name}"
            args = inspect.getfullargspec(func).args[1:]
            defaults = inspect.getfullargspec(func).defaults
            varkw = inspect.getfullargspec(func).varkw
            if defaults:
                len_defaults = len(defaults)
                for index, arg in enumerate(args[:-len_defaults]):
                    route = route + f"/{{_{index}}}" if route else f"{{_{index}}}"
                kwarg_keys = args[-len_defaults:]
            else:
                for index, arg in enumerate(args):
                    route = route + f"/{{_{index}}}" if route else f"{{_{index}}}"
                kwarg_keys = {}

            proxy = TechMicroService._create_rest_proxy(component, func, kwarg_keys, args, varkw)
            component.route(f"/{route}", methods=[method.upper()], authorizer=auth)(proxy)

    @staticmethod
    def _create_auth_proxy(component, auth_method):

        def proxy(auth_request):
            subsegment = xray_recorder.begin_subsegment(f"auth microservice")
            try:
                auth = auth_method(component, auth_request)
                if subsegment:
                    subsegment.put_metadata('result', auth)
            except Exception as e:
                print(f"Exception : {str(e)}")
                traceback.print_stack()
                if subsegment:
                    subsegment.add_exception(e, traceback.extract_stack())
                raise BadRequestError(str(e))
            finally:
                xray_recorder.end_subsegment()

            if type(auth) is bool:
                if auth:
                    return AuthResponse(routes=['*'], principal_id='user')
                return AuthResponse(routes=[], principal_id='user')
            elif type(auth) is list:
                return AuthResponse(routes=auth, principal_id='user')
            return auth

        proxy = update_wrapper(proxy, auth_method)
        proxy.__name__ = 'app'
        return component.authorizer(name='auth')(proxy)

    @staticmethod
    def _create_rest_proxy(component, func, kwarg_keys, args, varkw):

        def proxy(**kws):
            subsegment = xray_recorder.begin_subsegment(f"{func.__name__} microservice")
            try:
                if subsegment:
                    subsegment.put_metadata('headers', component.current_request.headers, "CoWorks")
                # Renames positionnal parameters
                req = component.current_request
                kwargs = {}
                for kw, value in kws.items():
                    param = args[int(kw[1:])]
                    kwargs[param] = value

                # Adds kwargs parameters
                if kwarg_keys:
                    if req.query_params:
                        params = {}
                        for k in req.query_params:
                            if k not in kwarg_keys and varkw is None:
                                raise BadRequestError(f"TypeError: got an unexpected keyword argument '{k}'")
                            value = req.query_params.getlist(k)
                            params[k] = value if len(value) > 1 else value[0]
                        kwargs = dict(**kwargs, **params)
                    if req.raw_body:
                        if hasattr(req.json_body, 'items'):
                            params = {}
                            for k, v in req.json_body.items():
                                if k not in kwarg_keys and varkw is None:
                                    raise BadRequestError(f"TypeError: got an unexpected keyword argument '{k}'")
                                params[k] = v
                            kwargs = dict(**kwargs, **params)
                        else:
                            kwargs[kwarg_keys[0]] = req.json_body
                return func(component, **kwargs)
            except Exception as e:
                print(f"Exception : {str(e)}")
                traceback.print_stack()
                if subsegment:
                    subsegment.add_exception(e, traceback.extract_stack())
                raise BadRequestError(str(e))
            finally:
                xray_recorder.end_subsegment()

        proxy = update_wrapper(proxy, func)
        proxy.__class_func__ = func
        return proxy

    def __call__(self, event, context):
        if 'type' in event and event['type'] == 'TOKEN':
            return self.__auth__(event, context)
        return super().__call__(event, context)


class At(Cron):
    def __init__(self, minutes, hours, day_of_month, month, day_of_week, year):
        super().__init__(minutes, hours, day_of_month, month, day_of_week, year)


class Every(Rate):
    def __init__(self, value, unit):
        super().__init__(value, unit)


class BizMicroService(Boto3Mixin, TechMicroService):
    """Chalice app to execute AWS Step Functions."""

    def __init__(self, arn, **kwargs):
        super().__init__(**kwargs)
        self._arn = arn
        self.__sfn_client__ = None

    def get_describe(self):
        res = self.sfn_client.describe_state_machine(stateMachineArn=self._arn)
        return json.dumps(res, indent=4, sort_keys=True, default=str)

    def get_execution(self, exe_arn):
        res = self.sfn_client.describe_execution(executionArn=exe_arn)
        return json.dumps(res, indent=4, sort_keys=True, default=str)

    def get_last(self, max_results=1):
        res = self.sfn_client.list_executions(stateMachineArn=self._arn, maxResults=int(max_results))
        return json.dumps(res, indent=4, sort_keys=True, default=str)

    def post_invoke(self, input="{}"):
        res = self.sfn_client.start_execution(stateMachineArn=self._arn, input=input)
        return res

    @property
    def sfn_client(self):
        if self.__sfn_client__ is None:
            self.__sfn_client__ = self.boto3_session.client('stepfunctions')
        return self.__sfn_client__

    def react(self, reactor_factory):
        if isinstance(reactor_factory, Every):
            def proxy(event,  context):
                print(event)
                return self.post_invoke()
            proxy.__name__ = "app"
            module = sys.modules[self.__module__]
            module.__setattr__("every", proxy)
            self.schedule(reactor_factory, name='every1')(proxy)


class Blueprint(ChaliceBlueprint):
    """Chalice blueprint created directly from class."""

    def __init__(self, **kwargs):
        import_name = kwargs.pop('import_name', self.__class__.__name__)
        super().__init__(import_name)

    @property
    def import_name(self):
        return self._import_name

    @property
    def component_name(self):
        return ''

    @property
    def current_app(self):
        return self._current_app
