import inspect
import json
import logging
import sys
import traceback
from functools import update_wrapper
from threading import Lock
from typing import Dict

from aws_xray_sdk.core import xray_recorder
from chalice import AuthResponse, BadRequestError, Rate, Cron
from chalice import Chalice, Blueprint as ChaliceBlueprint

from requests_toolbelt.multipart import MultipartEncoder

from .config import Config
from .mixins import CoworksMixin, AwsSFNSession
from .utils import begin_xray_subsegment, end_xray_subsegment
from .utils import class_auth_methods, class_rest_methods, class_attribute, trim_underscores

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class TechMicroService(CoworksMixin, Chalice):
    """Simple tech microservice created directly from class."""

    def __init__(self, app_name: str = None, config: Config = None, **kwargs):
        """ Initialize a technical microservice.
        :param app_name: Name used to identify the resource.
        :param config: Deployment configuration.
        :param kwargs: Other Chalice parameters.
        """
        app_name = app_name or self.__class__.__name__
        authorizer = kwargs.pop('authorizer', None)

        super().__init__(app_name, **kwargs)
        self.experimental_feature_flags.update([
            'BLUEPRINTS'
        ])

        self.config = config or Config()

        self.__auth__ = self._create_auth_proxy(self, authorizer) if authorizer else None

        # Blueprints added by names.
        self.blueprints = {}

        # Extensions defined by type's name (xriters, ..)
        self.extensions = {}

        # A list of functions that will be called at the first activation.
        # To register a function, use the :meth:`before_first_request` decorator.
        self.before_first_activation_funcs = []

        # A list of functions that will be called at the beginning of each activation.
        # To register a function, use the :meth:`before_activation` decorator.
        self.before_activation_funcs = []

        self.after_activation_funcs = []

        self._got_first_activation = False
        self._before_activation_lock = Lock()

        self.entries = {}
        self._add_route()
        self.sfn_call = False

        if "pytest" in sys.modules:
            xray_recorder.configure(context_missing="LOG_ERROR")

    @property
    def component_name(self):
        return class_attribute(self, 'url_prefix', '')

    @property
    def ms_type(self):
        return 'tech'

    @property
    def lambda_zip_file(self):
        return None

    @property
    def layer_zip_file(self):
        return None

    def register_blueprint(self, blueprint, **kwargs):
        if 'name_prefix' not in kwargs:
            kwargs['name_prefix'] = blueprint.component_name
        if 'url_prefix' not in kwargs:
            kwargs['url_prefix'] = f"/{blueprint.component_name}"

        self._add_route(blueprint, url_prefix=kwargs['url_prefix'])
        super().register_blueprint(blueprint, **kwargs)
        self.blueprints[blueprint.import_name] = blueprint

    def run(self, host='127.0.0.1', port=8000, project_dir='.', stage=None, debug=True):
        # chalice.cli and .cws packages not defined in deployment
        from chalice.cli import DEFAULT_STAGE_NAME
        from .cws.factory import CwsCLIFactory

        if debug:
            logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')

        stage = stage or DEFAULT_STAGE_NAME
        factory = CwsCLIFactory(self, project_dir, debug=debug)
        config = factory.mock_config_obj(self, stage)
        factory.run_local_server(self, config, host, port)

    def _add_route(self, component=None, url_prefix=None):
        if component is None:
            component = self

            # Adds class authorizer for every entries (if not already added before)
            auth = class_auth_methods(component)
            if auth and component.__auth__ is None:
                auth = TechMicroService._create_auth_proxy(component, auth)
                component.__auth__ = auth
        else:
            # Adds the current_app auth for blueprints
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

            proxy = component._create_rest_proxy(func, kwarg_keys, args, varkw)

            # complete all entries
            component.route(f"/{route}", methods=[method.upper()], authorizer=auth, cors=self.config.cors,
                            content_types=['multipart/form-data', 'application/json'])(proxy)
            if url_prefix:
                self.entries[f"{url_prefix}/{route}"] = (method.upper(), func)
            else:
                self.entries[f"/{route}"] = (method.upper(), func)

    @staticmethod
    def _create_auth_proxy(component, auth_method):

        def proxy(auth_activation):
            subsegment = begin_xray_subsegment(f"auth microservice")
            try:
                auth = auth_method(component, auth_activation)
                if subsegment:
                    subsegment.put_metadata('result', auth)
            except Exception as e:
                logger.info(f"Exception : {str(e)}")
                traceback.print_exc()
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

    def __call__(self, event, context):
        with self._before_activation_lock:
            if not self._got_first_activation:
                for func in self.before_first_activation_funcs:
                    func()
                self._got_first_activation = True

        for func in self.before_activation_funcs:
            func()

        res = self.handler(event, context)

        for func in self.after_activation_funcs:
            func()

        return res

    def handler(self, event, context):

        # authorization call
        if event.get('type') == 'TOKEN':
            if self.debug:
                print(f"Calling {self.app_name} for authorization")

            if self.__auth__:
                return self.__auth__(event, context)

            print(f"Undefined authorization method for {self.app_name} ")
            raise Exception('Unauthorized')

        # step function call
        if event.get('type') == 'CWS_SFN':
            if self.debug:
                print(f"Calling {self.app_name} by step function")

            self.sfn_call = True
            content_type = event['headers']['Content-Type']
            if content_type == 'application/json':
                body = event.get('body')
                event['body'] = json.dumps(self._get_data_on_s3(body)) if body else body
            elif content_type == 'multipart/form-data':
                if event.get('form-data'):
                    multi_parts = MultipartEncoder(self._set_multipart_content(event.get('form-data')))
                    event['headers']['Content-Type'] = multi_parts.content_type
                    event['body'] = multi_parts.to_string()
            else:
                raise BadRequestError(f"Undefined content type {content_type} for Step Function call")
        else:
            if self.debug:
                print(f"Calling {self.app_name} with event {event}")

        res = super().__call__(event, context)

        if self.sfn_call:
            if res['statusCode'] < 200 or res['statusCode'] >= 300:
                raise BadRequestError(f"Status code is {res['statusCode']} : {res['body']}")
            try:
                res['body'] = self._set_data_on_s3(json.loads(res['body']))
            except json.JSONDecodeError:
                pass

        if self.debug:
            print(f"Call {self.app_name} returns {res}")

        return res

    def before_first_activation(self, f):
        """Registers a function to be run before the first activation of the microservice.

        May be used as a decorator.

        The function will be called without any arguments and its return value is ignored.
        """

        self.before_first_activation_funcs.append(f)
        return f

    def before_activation(self, f):
        """Registers a function to run before each activation of the microservice.
        :param f:  Function added to the list.
        :return: None.

        May be used as a decorator.

        The function will be called without any arguments and its return value is ignored.
        """

        self.before_activation_funcs.append(f)
        return f

    def after_activation(self, f):
        """Registers a function to be run after each activation of the microservice.

        May be used as a decorator.

        The function will be called without any arguments and its return value is ignored.
        """

        self.after_activation_funcs.append(f)
        return f


class BizFactory(TechMicroService):
    """Tech microservice to create, update and trigger biz microservices."""

    def __init__(self, sfn_name, **kwargs):
        super().__init__(app_name=sfn_name, **kwargs)

        self.aws_profile = self.__sfn_client__ = self.__sfn_arn__ = None
        self.sfn_name = sfn_name
        self.biz: Dict[str, BizMicroService] = {}

        @self.before_first_activation
        def check_sfn():
            return self.sfn_arn

    @property
    def ms_type(self):
        return 'biz'

    @property
    def trigger_sources(self):

        def to_dict(name, trigger):
            return {'name': f"{self.sfn_name}-{name}", **trigger.to_dict()}

        return [to_dict(name, biz.trigger) for name, biz in self.biz.items()]

    @property
    def sfn_client(self):
        if self.__sfn_client__ is None:
            session = AwsSFNSession(profile_name=self.aws_profile, env_var_access_key="AWS_RUN_ACCESS_KEY_ID",
                                    env_var_secret_key="AWS_RUN_SECRET_KEY", env_var_region="AWS_RUN_REGION")
            self.__sfn_client__ = session.client
        return self.__sfn_client__

    @property
    def sfn_arn(self):
        if self.__sfn_arn__ is None:
            res = self.sfn_client.list_state_machines()
            while True:
                for sfn in res['stateMachines']:
                    if sfn['name'] == self.sfn_name:
                        self.__sfn_arn__ = sfn['stateMachineArn']
                        return self.__sfn_arn__

                next_token = res.get('nextToken')
                if next_token is None:
                    raise BadRequestError(f"Undefined step function : {self.sfn_name}")

                res = self.sfn_client.list_state_machines(nextToken=next_token)
        return self.__sfn_arn__

    def get_sfn_name(self):
        """Returns the name of the associated step function."""
        return self.sfn_name

    def get_sfn_arn(self):
        """Returns the arn of the associated step function."""
        return self.sfn_arn

    def get_biz_names(self):
        """Returns the list of biz microservices defined in the factory."""
        return [name for name in self.biz]

    def post_trigger(self, biz_name, data=None):
        """Manual triggering a biz microservice."""
        if self.debug:
            print(f"Manual triggering: {biz_name}")

        data = data or {}
        try:
            return self.biz[biz_name](data, {})
        except KeyError:
            if self.debug:
                print(f"Cannot found {biz_name} in services {[k for k in self.biz.keys()]}")
            raise BadRequestError(f"Cannot found {biz_name} biz microservice")

    def create(self, biz_name, trigger=None, data: dict = None, **kwargs):
        """Creates a biz microservice. If the trigger is not defined the microservice can only be triggered manually."""

        if biz_name in self.biz:
            raise BadRequestError(f"Biz microservice {biz_name} already defined for {self.sfn_name}")

        self.biz[biz_name] = BizMicroService(self, data, trigger, app_name=biz_name, **kwargs)
        return self.biz[biz_name]

    def invoke(self, data):
        res = self.sfn_client.start_execution(stateMachineArn=self.sfn_arn, input=json.dumps(data if data else {}))
        return json.dumps(res, indent=4, sort_keys=True, default=str)

    def handler(self, event, context):
        if 'detail-type' in event and event['detail-type'] == 'Scheduled Event':
            res_name = event['resources'][0].split('/')[-1]
            if not res_name.startswith(self.sfn_name):
                raise BadRequestError(f"Biz {self.sfn_name} called with resource {res_name}")

            biz_name = res_name[len(self.sfn_name) + 1:]
            if biz_name not in self.biz:
                raise BadRequestError(f"Unregistered biz : {biz_name}")

            if self.debug:
                print(f"Trigger: {biz_name}")

            return self.biz[biz_name](event, context)

        return super().handler(event, context)


class BizMicroService(TechMicroService):
    """Biz composed microservice activated by a reactor."""

    def __init__(self, biz_factory, data, trigger, **kwargs):
        super().__init__(**kwargs)
        self.biz_factory = biz_factory
        self.data = data
        self.trigger = trigger

    def handler(self, event, context):
        return self.biz_factory.invoke(self.data)


class Blueprint(CoworksMixin, ChaliceBlueprint):
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
