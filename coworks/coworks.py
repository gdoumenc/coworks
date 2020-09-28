import inspect
import json
import logging
import os
import sys
import traceback
from functools import update_wrapper
from threading import Lock
from typing import Dict, List, Union

from aws_xray_sdk.core import xray_recorder
from chalice import AuthResponse, BadRequestError, Rate, Cron
from chalice import Chalice, Blueprint as ChaliceBlueprint
from requests_toolbelt.multipart import MultipartEncoder

from .config import Config, DEFAULT_WORKSPACE
from .cws.error import CwsCommandError
from .mixins import CoworksMixin, AwsSFNSession
from .utils import begin_xray_subsegment, end_xray_subsegment
from .utils import class_auth_methods, class_rest_methods, class_attribute, trim_underscores

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class Blueprint(CoworksMixin, ChaliceBlueprint):
    """ Represents a blueprint, list of routes that will be added to microservice when registered.

    See :ref:`Blueprint <blueprint>` for more information.

    """

    def __init__(self, name=None, **kwargs):
        """Initialize a blueprint.

        :param kwargs: Other Chalice parameters.

        """
        import_name = name or self.__class__.__name__.lower()
        super().__init__(import_name)

    @property
    def name(self):
        return self._import_name

    @property
    def current_app(self):
        return self._current_app

    def deferred_init(self, workspace):
        for func in self.before_first_activation_funcs:
            self.current_app.before_first_activation(func)
        for func in self.before_activation_funcs:
            self.current_app.before_activation(func)
        for func in self.after_activation_funcs:
            self.current_app.after_activation(func)


class TechMicroService(CoworksMixin, Chalice):
    """Simple tech microservice created directly from class.
    
    See :ref:`tech` for more information.
    
    """

    def __init__(self, name: str = None, configs: Union[Config, List[Config]] = None, **kwargs):
        """ Initialize a technical microservice.
        :param name: Name used to identify the microservice.
        :param configs: Deployment configuration.
        :param workspace used for execution.
        :param kwargs: Other Chalice parameters.
        """
        name = name or self.__class__.__name__.lower()

        self.configs = configs or [Config()]
        if type(self.configs) is not list:
            self.configs = [configs]
        self.config = None

        super().__init__(app_name=name, **kwargs)

        # Blueprints and extended commands added
        self.experimental_feature_flags.update([
            'BLUEPRINTS'
        ])
        self.blueprints = {}
        self.commands = {}

        # App init deferered functions.
        self.deferred_inits = []
        self._got_first_activation = False
        self._before_activation_lock = Lock()

        self.entries = None
        self.sfn_call = False

        if "pytest" in sys.modules:
            xray_recorder.configure(context_missing="LOG_ERROR")

        self.__global_auth__ = None

    @property
    def name(self):
        return self.app_name

    @property
    def ms_type(self):
        return 'tech'

    def deferred_init(self, workspace):
        if self.entries is None:
            url_prefix = class_attribute(self, 'url_prefix', '')
            self._init_routes(workspace=workspace, url_prefix=url_prefix)
            for deferred_init in self.deferred_inits:
                deferred_init(workspace)
            for blueprint in self.iter_blueprints():
                blueprint.deferred_init(workspace)

    def register_blueprint(self, blueprint: Blueprint, authorizer=None, url_prefix=None, hide_routes=False,
                           **kwargs):
        """ Register a :class:`Blueprint` on the microservice.

        :param blueprint:
        :param authorizer:
        :param url_prefix:
        :param hide_routes:
        :param kwargs:
        :return:
        """
        if 'name_prefix' not in kwargs:
            kwargs['name_prefix'] = blueprint.name
        if 'url_prefix' not in kwargs:
            kwargs['url_prefix'] = f"/{blueprint.name}"

        if url_prefix in self.blueprints:
            raise NameError(f"A blueprint is already defined for the {url_prefix} prefix.")
        self.blueprints[url_prefix] = blueprint

        if not hide_routes:
            blueprint.__auth__ = self._create_auth_proxy(self, authorizer) if authorizer else None

        def deferred(workspace):
            if not hide_routes:
                self._init_routes(workspace=workspace, component=blueprint, url_prefix=url_prefix)
            Chalice.register_blueprint(self, blueprint, url_prefix=url_prefix)

        self.deferred_inits.append(deferred)

    def iter_blueprints(self):
        return self.blueprints.values()

    def execute(self, command, *, project_dir, module, service=None, workspace, output=None, error=None, **kwargs):
        """Executes a coworks command."""
        from coworks.cws.client import ProjectConfig

        project_config = ProjectConfig(command, project_dir)
        if not service:
            service = self.name
        cmd = project_config.get_command(self, module, service, workspace)
        if not cmd:
            raise CwsCommandError(f"The command {command} was not added to the microservice {self.name}.\n")

        client_params = {'project_dir': project_dir, 'module': module, 'service': service, 'workspace': workspace}
        complemented_args = project_config.missing_options(**client_params, **kwargs)
        cmd.execute(output=output, error=error, **client_params, **complemented_args)

    def _init_routes(self, *, workspace=DEFAULT_WORKSPACE, component=None, url_prefix=''):
        if self.config is None:
            for conf in self.configs:
                if conf.workspace == workspace:
                    self.config = conf
                    break
            if self.config is None:
                self.config = self.configs[0]

        if component is None:
            component = self

        # External authorizer has priority (forced)
        if self.config.auth:
            if self.__global_auth__ is None:
                self.__global_auth__ = self._create_auth_proxy(self, self.config.auth)
            auth = component.__auth__ = self.__global_auth__
        else:
            auth = class_auth_methods(component)
            if auth and component.__auth__ is None:
                auth = TechMicroService._create_auth_proxy(component, auth)
                component.__auth__ = auth
            auth = component.__auth__

        # Adds entrypoints
        if self.entries is None:
            self.entries = {}
        methods = class_rest_methods(component)
        for method, func in methods:
            if getattr(func, '__cws_hidden', False):
                continue

            # Get function's route
            if func.__name__ == method:
                route = f"{url_prefix}"
            else:
                name = func.__name__[len(method) + 1:]
                name = trim_underscores(name)  # to allow several functions with same route but different args
                name = name.replace('_', '/')
                route = f"{url_prefix}/{name}" if url_prefix else f"{name}"

            # Get parameters
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
            if not route.startswith('/'):
                route = '/' + route
            self.route(f"{route}", methods=[method.upper()], authorizer=auth, cors=self.config.cors,
                       content_types=list(self.config.content_type))(proxy)
            if url_prefix:
                self.entries[f"{url_prefix}{route}"] = (method.upper(), func)
            else:
                self.entries[f"{route}"] = (method.upper(), func)

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
        """Lambda handler."""
        self.do_before_first_activation()
        self.do_before_activation()
        res = self.handler(event, context)
        self.do_after_activation()
        return res

    def handler(self, event, context):
        """Main microservice entry point."""

        # authorization call
        if event.get('type') == 'TOKEN':
            if self.debug:
                print(f"Calling {self.name} for authorization")

            if self.__auth__:
                return self.__auth__(event, context)

            print(f"Undefined authorization method for {self.name} ")
            return 'Unauthorized', 403

        # step function call
        if event.get('type') == 'CWS_SFN':
            if self.debug:
                print(f"Calling {self.name} by step function")

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
                print(f"Calling {self.name} with event {event}")

        res = super().__call__(event, context)

        if self.sfn_call:
            if res['statusCode'] < 200 or res['statusCode'] >= 300:
                raise BadRequestError(f"Status code is {res['statusCode']} : {res['body']}")
            try:
                res['body'] = self._set_data_on_s3(json.loads(res['body']))
            except json.JSONDecodeError:
                pass

        if self.debug:
            print(f"Call {self.name} returns {res}")

        return res

    def deferred(self, f):
        """Registers a function to be run once the microservice will be initialized.

        May be used as a decorator.

        The function will be called with one parameter, the workspace, and its return value is ignored.
        """

        self.deferred_inits.append(f)
        return f

    def do_before_first_activation(self):
        """Calls all before first activation functions."""
        if self._got_first_activation:
            return

        # lock needed only if boolean may change value
        with self._before_activation_lock:
            workspace = os.environ['WORKSPACE']
            self.deferred_init(workspace=workspace)

            if not self._got_first_activation:
                for func in self.before_first_activation_funcs:
                    func()
                self._got_first_activation = True

    def do_before_activation(self):
        """Calls all before activation functions."""
        for func in self.before_activation_funcs:
            func()

    def do_after_activation(self):
        """Calls all after activation functions."""
        for func in self.after_activation_funcs:
            func()


class BizFactory(TechMicroService):
    """Tech microservice to create, update and trigger biz microservices.
    """

    def __init__(self, sfn_name, **kwargs):
        super().__init__(name=sfn_name, **kwargs)

        self.aws_profile = self.__sfn_client__ = self.__sfn_arn__ = None
        self.sfn_name = sfn_name
        self.biz: Dict[str, BizMicroService] = {}

        @self.before_first_activation
        def check_sfn():
            return self.sfn_arn

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
                    if sfn['name'] == os.environ['SFN_NAME']:
                        self.__sfn_arn__ = sfn['stateMachineArn']
                        return self.__sfn_arn__

                next_token = res.get('nextToken')
                if next_token is None:
                    raise BadRequestError(f"Undefined step function : {self.sfn_name}")

                res = self.sfn_client.list_state_machines(nextToken=next_token)
        return self.__sfn_arn__

    @property
    def trigger_sources(self):

        def to_dict(name, trigger):
            return {'name': f"{self.sfn_name}-{name}", **trigger.to_dict()}

        return [to_dict(name, biz.trigger) for name, biz in self.biz.items()]

    def create(self, biz_name, trigger=None, configs: List[Config] = None, **kwargs):
        """Creates a biz microservice. If the trigger is not defined the microservice can only be triggered manually."""

        if biz_name in self.biz:
            raise BadRequestError(f"Biz microservice {biz_name} already defined for {self.sfn_name}")

        self.biz[biz_name] = BizMicroService(self, trigger, configs, name=biz_name, **kwargs)
        return self.biz[biz_name]

    def invoke(self, data):
        res = self.sfn_client.start_execution(stateMachineArn=self.sfn_arn, input=json.dumps(data if data else {}))
        return json.dumps(res, indent=4, sort_keys=True, default=str)


class BizMicroService(TechMicroService):
    """Biz composed microservice activated by a reactor.
    """

    def __init__(self, biz_factory, trigger, configs, **kwargs):
        super().__init__(**kwargs)
        self.biz_factory = biz_factory
        self.configs = configs
        self.trigger = trigger

    @property
    def ms_type(self):
        return 'biz'

    @property
    def trigger_source(self):
        return self.trigger.to_dict()

    def get_sfn_name(self):
        """Returns the name of the associated step function."""
        return self.biz_factory.sfn_name

    def get_sfn_arn(self):
        """Returns the arn of the associated step function."""
        return self.biz_factory.sfn_arn

    def get_biz_names(self):
        """Returns the list of biz microservices defined in the factory."""
        return [name for name in self.biz_factory]

    def get_default_data(self):
        try:
            workspace = os.environ['WORKSPACE']
        except KeyError:
            raise EnvironmentError("environment variable WORKSPACE is not defined")
        try:
            default_data = next(c.data for c in self.configs if c.workspace == workspace)
        except StopIteration:
            print(f"No configuration found for workspace {workspace} in {self.configs}")
            default_data = {}
        except KeyError:
            default_data = {}
        return default_data

    def post_trigger(self, data=None):
        data = data or {}
        data.update(self.get_default_data())
        return self.biz_factory.invoke(data)

    def handler(self, event, context):
        if 'detail-type' in event and event['detail-type'] == 'Scheduled Event':
            if self.debug:
                print(f"Trigger: {self.biz_factory.sfn_name}")
            return self.biz_factory.invoke(self.get_default_data())

        return super().handler(event, context)


def hide(f):
    """Hide a route of the microservice.

     May be used as a decorator.

     Usefull when creating inherited microservice.
     """

    setattr(f, '__cws_hidden', True)
    return f


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
