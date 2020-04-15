import cgi
import inspect
import io
import json
import logging
import os
import sys
import traceback
from collections import namedtuple
from functools import update_wrapper
from threading import Lock
from typing import Dict, Union

from aws_xray_sdk.core import xray_recorder
from chalice import Chalice, Blueprint as ChaliceBlueprint, NotFoundError
from chalice import Response, AuthResponse, BadRequestError, Rate, Cron
from requests_toolbelt.multipart import decoder

from .mixins import Boto3Mixin
from .utils import begin_xray_subsegment, end_xray_subsegment
from .utils import class_auth_methods, class_rest_methods, class_attribute, trim_underscores

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class TechMicroService(Chalice):
    """Simple microservice app created directly from class."""

    def __init__(self, app_name=None, **kwargs):
        app_name = app_name or self.__class__.__name__
        authorizer = kwargs.pop('authorizer', None)

        super().__init__(app_name, **kwargs)
        self.experimental_feature_flags.update([
            'BLUEPRINTS'
        ])

        self.__auth__ = self._create_auth_proxy(self, authorizer) if authorizer else None
        self.debug = kwargs.pop('debug', False)
        self.blueprints = {}
        self.extensions = {}

        self.entries = {}
        self._add_route()

        self.before_first_request_funcs = []
        self.before_request_funcs = []
        self.after_request_funcs = []

        self._got_first_request = False
        self._before_request_lock = Lock()

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
        if 'name_prefix' not in kwargs:
            kwargs['name_prefix'] = blueprint.component_name
        if 'url_prefix' not in kwargs:
            kwargs['url_prefix'] = f"/{blueprint.component_name}"

        self._add_route(blueprint, url_prefix=kwargs['url_prefix'])
        super().register_blueprint(blueprint, **kwargs)
        self.blueprints[blueprint.import_name] = blueprint

    def run(self, host='127.0.0.1', port=8000, project_dir='.', stage=None, debug=True):
        # chalice.cli package not defined in deployment package
        from chalice.cli import DEFAULT_STAGE_NAME
        from .cli.factory import CWSFactory

        if debug:
            logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')

        stage = stage or DEFAULT_STAGE_NAME
        factory = CWSFactory(self, project_dir, debug=debug)
        config = factory.create_config_obj(chalice_stage_name=stage)
        factory.run_local_server(config, host, port)

    def _add_route(self, component=None, url_prefix=None):
        if component is None:
            component = self

            # Adds class authorizer for every entries (if not defined at creation)
            auth = class_auth_methods(component)
            if auth and component.__auth__ is None:
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
                name = trim_underscores(name)  # to allow several functions with same route but different args
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

            # complete all entries
            component.route(f"/{route}", methods=[method.upper()], authorizer=auth,
                            content_types=['multipart/form-data', 'application/json'])(proxy)
            if url_prefix:
                self.entries[f"{url_prefix}/{route}"] = (method.upper(), func)
            else:
                self.entries[f"/{route}"] = (method.upper(), func)

    @staticmethod
    def _create_auth_proxy(component, auth_method):

        def proxy(auth_request):
            subsegment = begin_xray_subsegment(f"auth microservice")
            try:
                auth = auth_method(component, auth_request)
                if subsegment:
                    subsegment.put_metadata('result', auth)
            except Exception as e:
                logger.info(f"Exception : {str(e)}")
                traceback.print_stack()
                if subsegment:
                    subsegment.add_exception(e, traceback.extract_stack())
                raise BadRequestError(str(e))
            finally:
                end_xray_subsegment()

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
            if component.debug:
                print(f"Calling {func} for {component}")

            subsegment = begin_xray_subsegment(f"{func.__name__} microservice")
            try:
                if subsegment:
                    subsegment.put_metadata('headers', component.current_request.headers, "CoWorks")

                # Renames positionnal parameters (index added in label)
                kwargs = {}
                for kw, value in kws.items():
                    param = args[int(kw[1:])]
                    kwargs[param] = value

                # Adds kwargs parameters
                def check_param_expected_in_lambda(param_name):
                    """Alerts when more parameters than expected are defined in request."""
                    if param_name not in kwarg_keys and varkw is None:
                        raise BadRequestError(f"TypeError: got an unexpected keyword argument '{param_name}'")

                def add_param(param_name, param_value):
                    check_param_expected_in_lambda(param_name)
                    if param_name in params:
                        if isinstance(params[param_name], list):
                            params[param_name].append(param_value)
                        else:
                            params[param_name] = [params[param_name], param_value]
                    else:
                        params[param_name] = param_value

                req = component.current_request
                if kwarg_keys or varkw:
                    params = {}
                    if req.raw_body:  # POST request
                        content_type = req.headers['content-type']
                        if content_type.startswith('multipart/form-data'):
                            multipart_decoder = decoder.MultipartDecoder(req.raw_body, content_type)
                            for part in multipart_decoder.parts:
                                headers = {k.decode('utf-8'): cgi.parse_header(v.decode('utf-8')) for k, v in
                                           part.headers.items()}
                                content = part.content
                                _, content_disposition_params = headers['Content-Disposition']
                                part_content_type, _ = headers.get('Content-Type', (None, None))
                                name = content_disposition_params['name']

                                if 'filename' not in content_disposition_params:
                                    add_param(name, content.decode('utf-8'))
                                else:
                                    # content in a file (s3 or plain text)
                                    if part_content_type == 'text/s3':
                                        boto3 = Boto3Mixin()
                                        boto3_session = boto3.boto3_session
                                        client = boto3_session.client('s3')
                                        s3_object = client.get_object(Bucket=content.decode('utf-8').split('/', 1)[0],
                                                                      Key=content.decode('utf-8').split('/', 1)[1])
                                        if not s3_object:
                                            return NotFoundError(f"File {content.decode('utf-8')} not found on s3")
                                        file = io.BytesIO(s3_object['Body'].read())
                                        file.name = content.decode('utf-8').split('/')[-1]
                                        mime_type = s3_object['ContentType']
                                    else:
                                        file = io.BytesIO(content)
                                        file.name = content_disposition_params['filename']
                                        mime_type = part_content_type
                                    FileParam = namedtuple('FileParam', ['file', 'mime_type'])
                                    add_param(name, FileParam(file, mime_type))
                            kwargs = dict(**kwargs, **params)

                        elif content_type.startswith('application/json'):
                            if hasattr(req.json_body, 'items'):
                                params = {}
                                for k, v in req.json_body.items():
                                    add_param(k, v)
                                kwargs = dict(**kwargs, **params)
                            else:
                                kwargs[kwarg_keys[0]] = req.json_body
                        elif content_type.startswith('text/plain'):
                            kwargs[kwarg_keys[0]] = req.json_body

                    else:  # GET request

                        # adds parameters from qurey parameters
                        for k in req.query_params or []:
                            value = req.query_params.getlist(k)
                            add_param(k, value if len(value) > 1 else value[0])
                        kwargs = dict(**kwargs, **params)

                resp = func(component, **kwargs)
                return TechMicroService._convert_response(resp)

            except Exception as e:
                print(f"Exception : {str(e)}")
                traceback.print_stack()
                if subsegment:
                    subsegment.add_exception(e, traceback.extract_stack())
                raise BadRequestError(str(e))
            finally:
                end_xray_subsegment()

        proxy = update_wrapper(proxy, func)
        proxy.__class_func__ = func
        return proxy

    def __call__(self, event, context):
        if self.debug:
            print(f"Event: {event}")

        with self._before_request_lock:
            if not self._got_first_request:
                for func in self.before_first_request_funcs:
                    func()
                self._got_first_request = True

        for func in self.before_request_funcs:
            func()

        res = self.handler(event, context)

        for func in self.after_request_funcs:
            func()

        return res

    def handler(self, event, context):
        if 'type' in event and event['type'] == 'TOKEN':
            if self.debug:
                print(f"Calling {self.app_name} authorization")
            if self.__auth__:
                return self.__auth__(event, context)
            print(f"Undefined authorization method for {self.app_name} ")
            raise Exception('Unauthorized')

        if self.debug:
            print(f"Calling {self.app_name} with event {event}")

        res = super().__call__(event, context)

        if self.debug:
            print(f"Call {self.app_name} returns {res}")

        return res

    def before_first_request(self, f):
        """Registers a function to be run before the first request to this instance of the application.
           The function will be called without any arguments and its return value is ignored."""

        self.before_first_request_funcs.append(f)
        return f

    def before_request(self, f):
        """Registers a function to be run before each request to this instance of the application.
           The function will be called without any arguments and its return value is ignored."""

        self.before_request_funcs.append(f)
        return f

    def after_request(self, f):
        """Registers a function to be run before each request to this instance of the application.
           The function will be called without any arguments and its return value is ignored."""

        self.after_request_funcs.append(f)
        return f

    @staticmethod
    def _convert_response(resp):
        if type(resp) is tuple:
            status_code = resp[1]
            if len(resp) == 2:
                return Response(body=resp[0], status_code=status_code)
            else:
                return Response(body=resp[0], status_code=status_code, headers=resp[2])

        elif not isinstance(resp, Response):
            return Response(body=resp)

        return resp


class BizFactory(Boto3Mixin, TechMicroService):
    """Microservice to create and update biz microservices."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.__sfn_client__ = None
        self.services: Dict[str, BizMicroService] = {}

    @property
    def trigger_sources(self):
        return [source for biz in self.services.values() for source in biz.trigger_sources]

    @property
    def sfn_client(self):
        if self.__sfn_client__ is None:
            self.__sfn_client__ = self.boto3_session.client('stepfunctions')
        return self.__sfn_client__

    def get_sfn(self, sfn_name=None):
        if self.debug:
            print(f"Search for Step Function: {sfn_name}")

        if sfn_name is None:
            return

        res = self.sfn_client.list_state_machines()
        while True:
            for sfn in res['stateMachines']:
                if sfn['name'] == sfn_name:
                    return sfn['stateMachineArn']

            next_token = res.get('nextToken')
            if next_token is None:
                raise BadRequestError(f"Undefined step function : {sfn_name}")

            res = self.sfn_client.list_state_machines(nextToken=next_token)

    def post_trigger(self, name, data=None):
        """Manual triggering a reactor."""
        if self.debug:
            print(f"Manual triggering: {name}")

        data = data or {}
        return self.services[name](data, {})

    def create(self, sfn_name, reactor_name, trigger=None, data: dict = None, **kwargs):
        """Creates a named reactor. If the trigger is not defined the service can only be trigger by hand."""
        if self.debug:
            print(f"Create {sfn_name}-{reactor_name} reactor")

        biz = BizMicroService(sfn_name, **kwargs)
        reactor = biz.add_reactor(reactor_name, trigger, data)
        self.services[reactor.full_name] = biz
        return biz

    def handler(self, event, context):
        if self.debug:
            print(f"Event: {event}")

        if 'detail-type' in event and event['detail-type'] == 'Scheduled Event':
            full_reactor_name = event['resources'][0].split('/')[-1]
            if full_reactor_name not in self.services:
                raise BadRequestError(f"Unregistered reactor : {full_reactor_name}")

            if self.debug:
                print(f"Trigger: {full_reactor_name}")

            return self.services[full_reactor_name](event, context)

        return super().handler(event, context)


class BizMicroService(BizFactory):
    """Chalice app to execute AWS Step Functions."""

    def __init__(self, sfn_name, **kwargs):
        if 'app_name' not in kwargs:
            kwargs['app_name'] = sfn_name
        super().__init__(**kwargs)
        self.sfn_name = sfn_name
        self.sfn_arn = None
        self.reactors: Dict[str, Reactor] = {}

        @self.before_first_request
        def get_sfn_arn():
            if self.debug:
                print(f"Search for Step Function: {sfn_name}")

            if sfn_name is None:
                return

            res = self.sfn_client.list_state_machines()
            while True:
                for sfn in res['stateMachines']:
                    if sfn['name'] == sfn_name:
                        self.sfn_arn = sfn['stateMachineArn']
                        return

                next_token = res.get('nextToken')
                if next_token is None:
                    raise BadRequestError(f"Undefined step function : {sfn_name}")

                res = self.sfn_client.list_state_machines(nextToken=next_token)

    @property
    def trigger_sources(self):
        return [reactor.to_dict() for reactor in self.reactors.values()]

    def get_describe(self):
        res = self.sfn_client.describe_state_machine(stateMachineArn=self.sfn_arn)
        return json.dumps(res, indent=4, sort_keys=True, default=str)

    def get_execution(self, exe_arn):
        res = self.sfn_client.describe_execution(executionArn=exe_arn)
        return json.dumps(res, indent=4, sort_keys=True, default=str)

    def get_last(self, max_results=1):
        res = self.sfn_client.list_executions(stateMachineArn=self.sfn_arn, maxResults=int(max_results))
        return json.dumps(res, indent=4, sort_keys=True, default=str)

    def post_invoke(self, input="{}"):
        res = self.sfn_client.start_execution(stateMachineArn=self.sfn_arn, input=input)
        return json.dumps(res, indent=4, sort_keys=True, default=str)

    def add_reactor(self, reactor_name, source=None, data=None):
        full_reactor_name = f"{self.sfn_name}-{reactor_name}"
        if full_reactor_name in self.reactors:
            raise Exception(f"Reactor {reactor_name} already defined for {self.sfn_name}.")

        def proxy(event, context):
            if self.debug:
                print(f"Calling {self.app_name} from scheduled event")

            return self.post_invoke(input=json.dumps(data) if data is not None else "{}")

        reactor = self.reactors[full_reactor_name] = Reactor(full_reactor_name, proxy, source)
        return reactor

    def handler(self, event, context):
        if self.debug:
            print(f"Event: {event}")

        if 'detail-type' in event and event['detail-type'] == 'Scheduled Event':
            full_reactor_name = event['resources'][0].split('/')[-1]
            if full_reactor_name not in self.reactors:
                raise BadRequestError(f"Unregistered reactor : {full_reactor_name}")

            if self.debug:
                print(f"Trigger: {full_reactor_name}")

            return self.reactors[full_reactor_name].trigger(event, context)

        return super().handler(event, context)


class Blueprint(ChaliceBlueprint):
    """Chalice blueprint created directly from class."""

    def __init__(self, **kwargs):
        import_name = kwargs.pop('import_name', self.__class__.__name__)
        super().__init__(import_name)

        self.debug = kwargs.pop('debug', False)

    @property
    def import_name(self):
        return self._import_name

    @property
    def component_name(self):
        return ''

    @property
    def current_app(self):
        return self._current_app


class Reactor:
    """A reactor is a lambda to call biz microservice."""

    def __init__(self, full_name, proxy, source=None):
        self.full_name = full_name
        self.source = source
        self.__proxy = proxy

    def trigger(self, *args):
        return self.__proxy(*args)

    def to_dict(self):
        return dict(name=self.full_name, **self.source.to_dict())


class Once:
    ...


class At(Cron):
    def __init__(self, minutes=0, hours=1, day_of_month=None, month=None, day_of_week=None, year=None):
        super().__init__(minutes, hours, day_of_month, month, day_of_week, year)

    def to_dict(self):
        return {
            'source': 'at',
            'value': self.to_string(),
        }


class Every(Rate):
    def __init__(self, value, unit):
        super().__init__(value, unit)

    def to_dict(self):
        return {
            'source': 'every',
            'value': self.to_string(),
        }
