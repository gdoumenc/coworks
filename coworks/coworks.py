import re
import json
import os
from dataclasses import dataclass
from functools import wraps
from typing import Callable
from typing import Dict, List, Union, Optional

from chalice import AuthResponse, Response, Rate, Cron
from chalice import Chalice, Blueprint as ChaliceBlueprint
from chalice.app import AuthRequest

from . import aws
from .config import Config, DEFAULT_PROJECT_DIR, DEFAULT_WORKSPACE
from .error import CwsError
from .mixins import CoworksMixin
from .utils import trim_underscores, HTTP_METHODS

ENTRY_REGEXP = '[^0-9a-zA-Z_]'


def entry(fun):
    """Decorator to create a microservice entrypoint from function name."""
    name = fun.__name__.upper()
    for method in HTTP_METHODS:
        if name == method:
            fun.__CWS_METHOD = method
            fun.__CWS_PATH = ''
            return fun
        if name.startswith(f'{method}_'):
            fun.__CWS_METHOD = method
            name = fun.__name__[len(method) + 1:]
            name = trim_underscores(name)  # to allow several functions with different args
            fun.__CWS_PATH = name.replace('_', '/')
            return fun
    raise AttributeError(f"The function name {fun.__name__} doesn't start with a HTTP method name.")


@dataclass
class Entry:
    """An entry is an API entry defined on a microservice, with a specific authorization function and
    its response function."""

    auth: Callable
    fun: Callable


@dataclass
class ScheduleEntry:
    """An schedule entry is an EventBridge entry defined on a microservice, with the schedule expression,
    its description and its response function."""

    name: str
    exp: str
    desc: str
    fun: Callable


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

    @property
    def logger(self):
        return self._current_app.logger

    def entry(self, route):
        return self.current_app.entry(route)

    def deferred_init(self, workspace):
        for func in self.before_first_activation_funcs:
            self.current_app.before_first_activation(func)
        for func in self.before_activation_funcs:
            self.current_app.before_activation(func)
        for func in self.after_activation_funcs:
            self.current_app.after_activation(func)
        for func in self.handle_exception_funcs:
            self.current_app.handle_exception_funcs(func)


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
        self.blueprints: Dict[str, Blueprint] = {}
        self.commands = {}

        # App init deferered functions.
        self.deferred_inits = []
        self._got_first_activation = False

        self.entries: Optional[Dict[str, Dict[str, Entry]]] = None
        self.schedule_entries: Dict[str, ScheduleEntry] = {}
        self.sfn_call = False

    @property
    def name(self):
        return self.app_name

    @property
    def ms_type(self):
        return 'tech'

    def get_config(self, workspace):
        for conf in self.configs:
            if conf.is_valid_for(workspace):
                return conf
        return self.configs[0]

    def deferred_init(self, workspace):
        if self.entries is None:

            # Set workspace config
            self.config = self.get_config(workspace)

            # Initializes routes and defered initializations
            self._init_routes(self)
            for deferred_init in self.deferred_inits:
                deferred_init(workspace)
            for blueprint in self.blueprints.values():
                blueprint.deferred_init(workspace)

    def register_blueprint(self, blueprint: Blueprint, name=None, url_prefix='', hide_routes=False):
        """ Register a :class:`Blueprint` on the microservice.

        :param blueprint: blueprint to register.
        :param name: name registration (needed to retrieve it).
        :param url_prefix: url prefix for the routes added (must be unique for each blueprints).
        :param hide_routes:
        :return:
        """
        name = name or blueprint.name
        if name in self.blueprints:
            raise NameError(f"A blueprint is already defined with the name : {name}.")
        self.blueprints[name] = blueprint

        def deferred(workspace):
            """Global authorization function for the blueprint may be redefined or is the service's one."""
            blueprint._init_routes(self, url_prefix=url_prefix, hide_routes=hide_routes)
            super(TechMicroService, self).register_blueprint(blueprint, url_prefix=url_prefix)

        self.deferred_inits.append(deferred)

    # noinspection PyMethodOverriding
    def schedule(self, exp, *, name=None, description=None, workspaces=None):
        """Registers a function to be run before the first activation of the microservice.

        May be used as a decorator.

        The function will be called with event and context positional arguments and its return value is ignored.
        """

        def decorator(f):
            schedule_name = name if name else exp
            desc = description if description else f.__doc__
            entry_key = re.sub(ENTRY_REGEXP, '', exp)
            self.schedule_entries[f"{f.__name__}_{entry_key}"] = ScheduleEntry(schedule_name, exp, desc, f)
            return f

        return decorator

    def add_entry(self, path, method, auth, fun):
        self.entries[path][method] = Entry(auth, fun)

    def execute(self, command, *, project_dir=DEFAULT_PROJECT_DIR, module=None, service=None,
                workspace=DEFAULT_WORKSPACE, output=None, error=None, **options):
        from .cws.client import CwsClientOptions
        from .cws.error import CwsCommandError

        # Executes a coworks command.
        module = __name__ if module is None else module
        service = self.name if service is None else service
        cws_options = CwsClientOptions({"project_dir": project_dir, 'module': module, 'service': service})
        service_config = cws_options.get_service_config(module, service, workspace)
        if type(command) is str:
            cmd = service_config.get_command(command, self)
            if not cmd:
                raise CwsCommandError(f"The command {command} was not added to the microservice {self.name}.\n")
        else:
            cmd = command
        command_options = service_config.get_command_options(command)
        execute_options = {**command_options, **options}
        cmd.execute(output=output, error=error, **execute_options)

    def __call__(self, event, context):
        """Lambda handler."""
        try:
            self.do_before_first_activation(event, context)
            self.do_before_activation(event, context)
            response = self.handler(event, context)
            return self.do_after_activation(response)
        except Exception as e:
            self.log.error(f"exception: {e}")
            response = self.do_handle_exception(event, context, e)
            if response is None:
                raise
            return response

    def handler(self, event, context):
        """Main microservice entry point."""

        if event.get('type') == 'TOKEN':
            return self._token_handler(event, context)
        if event.get('type') == 'CWS_SCHEDULE_EVENT':
            return self._schedule_event_handler(event, context)
        return self._api_handler(event, context)

    def deferred(self, f):
        """Registers a function to be run once the microservice will be initialized.

        May be used as a decorator.

        The function will be called with one parameter, the workspace, and its return value is ignored.
        """

        self.deferred_inits.append(f)
        return f

    def do_before_first_activation(self, event, context):
        """Calls all before first activation functions."""
        if self._got_first_activation:
            return

        workspace = os.environ['WORKSPACE']
        self.deferred_init(workspace=workspace)

        if not self._got_first_activation:
            for func in self.before_first_activation_funcs:
                func(event, context)
            self._got_first_activation = True

    def do_before_activation(self, event, context):
        """Calls all before activation functions."""
        for func in self.before_activation_funcs:
            func(event, context)

    def do_after_activation(self, response):
        """Calls all after activation functions."""
        for func in reversed(self.after_activation_funcs):
            resp = func(response)
            if resp is not None:
                response = resp
        return response

    def do_handle_exception(self, event, context, exc):
        """Calls all exception handlers."""
        for func in reversed(self.handle_exception_funcs):
            resp = func(event, context, exc)
            if resp is not None:
                return resp

    def _entry(self, path: str, method: str) -> Optional[Entry]:
        """Finds the entry corresponding to the route."""
        pathes = [x for x in path.split('/') if x]
        for entry, result in self.entries.items():
            entry_pathes = [x for x in entry.split('/') if x]
            if len(pathes) != len(entry_pathes):
                continue

            found = True
            for index, path in enumerate(entry_pathes):
                if index < len(pathes):
                    if path.startswith('{') or path == pathes[index]:
                        continue
                found = False
                break

            if found:
                return result[method]
        return None

    def _token_handler(self, event, context):
        """Authorization handler."""
        self.log.debug(f"Calling {self.name} for authorization")

        try:
            *_, method, route = event.get('methodArn').split('/', 3)
            authorizer = self._entry(f'/{route}', method).auth
            return authorizer(event, context)
        except Exception as e:
            self.log.debug(f"Error in authorization handler for {self.name} : {e}")
            request = AuthRequest(event['type'], event['authorizationToken'], event['methodArn'])
            return AuthResponse(routes=[], principal_id='user').to_dict(request)

    def _schedule_event_handler(self, event, context):
        """Schedule event handler."""
        self.log.debug(f"Calling {self.name} by event bridge")

        try:
            entry_name = event.get('entry_name')
            return self.schedule_entries[entry_name].fun(event.get('schedule_name'))
        except Exception as e:
            self.log.debug(f"Error in schedule event handler for {self.name} : {e}")
            raise

    def _api_handler(self, event, context):
        """API rest handler."""
        self.log.debug(f"Calling {self.name} by api")

        try:
            # Chalice accepts only string for body
            if type(event['body']) is dict:
                event['body'] = json.dumps(event['body'])

            res = super().__call__(event, context)
            workspace = os.getenv('WORKSPACE')
            if workspace:
                res['headers']['x-cws-workspace'] = workspace

            self.log.debug(f"Call {self.name} returns {res}")
            return res
        except Exception as e:
            self.log.debug(f"Error in api handler for {self.name} : {e}")
            raise


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
            session = aws.AwsSFNSession(profile_name=self.aws_profile, env_var_access_key="AWS_RUN_ACCESS_KEY_ID",
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
                    err_msg = f"Undefined step function : {self.sfn_name}"
                    return Response(body=err_msg, status_code=400)

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
            raise CwsError(f"Biz microservice {biz_name} already defined for {self.sfn_name}")

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
            self.log.debug(f"No configuration found for workspace {workspace} in {self.configs}")
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
                self.log.debug(f"Trigger: {self.biz_factory.sfn_name}")
            return self.biz_factory.invoke(self.get_default_data())

        return super().handler(event, context)


def hide(f):
    """Hide a route of the microservice.

     May be used as a decorator.

     Usefull when creating inherited microservice.
     """

    setattr(f, '__cws_hidden', True)
    return f


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
