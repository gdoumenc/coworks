from dataclasses import dataclass

import json
import os
import re
import requests
from chalice import AuthResponse
from chalice import Chalice, Blueprint as ChaliceBlueprint
from chalice.app import AuthRequest
from typing import Callable
from typing import Dict, List, Union, Optional

from .config import Config, LocalConfig, DevConfig, ProdConfig, DEFAULT_PROJECT_DIR, DEFAULT_WORKSPACE
from .mixins import CoworksMixin
from .utils import trim_underscores, HTTP_METHODS

ENTRY_REGEXP = '[^0-9a-zA-Z_]'


#
# Decorators
#

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


def hide(f):
    """Hide a route of the microservice.

     May be used as a decorator.

     Usefull when creating inherited microservice.
     """

    setattr(f, '__cws_hidden', True)
    return f


#
# Classes
#

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
            self.current_app.handle_exception(func)


class TechMicroService(CoworksMixin, Chalice):
    """Simple tech microservice.
    
    See :ref:`tech` for more information.
    
    """

    def __init__(self, name: str = None, configs: Union[Config, List[Config]] = None, **kwargs):
        """ Initialize a technical microservice.
        :param name: Name used to identify the microservice.
        :param configs: Deployment configurations.
        :param kwargs: Other Chalice parameters.
        """
        name = name or self.__class__.__name__.lower()

        self.configs = configs or [LocalConfig(), DevConfig(), ProdConfig()]
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
        self.entries: Optional[Dict[str, Dict[str, Entry]]] = None

        # App init deferered functions.
        self.deferred_inits = []
        self._got_first_activation = False

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
        return Config()

    def deferred_init(self, workspace):
        if self.entries is None:
            self.entries = {}

            # Set workspace config
            self.config = self.get_config(workspace)

            # Initializes routes and defered initializations
            self._init_routes(self)
            for deferred_init in self.deferred_inits:
                deferred_init(workspace)
            for blueprint in self.blueprints.values():
                blueprint.deferred_init(workspace)

    def register_blueprint(self, blueprint: Blueprint, name=None, url_prefix='', hide_routes=False, show_routes=None):
        """ Register a :class:`Blueprint` on the microservice.

        :param blueprint: blueprint to register.
        :param name: name registration (needed to retrieve it).
        :param url_prefix: url prefix for the routes added (must be unique for each blueprints).
        :param hide_routes: Hide all routes in blueprint.
        :param show_routes:
        :return:
        """
        name = name or blueprint.name
        if name in self.blueprints:
            raise NameError(f"A blueprint is already defined with the name : {name}.")
        self.blueprints[name] = blueprint

        def deferred(workspace):
            if not hide_routes:
                blueprint._init_routes(self, url_prefix=url_prefix)

            # use old syntax for super as local server changes type
            super(TechMicroService, self).register_blueprint(blueprint, url_prefix=url_prefix)

        self.deferred_inits.append(deferred)

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
            self.do_after_activation(response)
            return self._convert_response(response)
        except Exception as e:
            self.log.error(f"exception: {e}")
            response = self.do_handle_exception(event, context, e)
            if response is None:
                raise
            return self._convert_response(response)

    def handler(self, event, context):
        """Main microservice entry point."""

        if event.get('type') == 'TOKEN':
            return self._token_handler(event, context)
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
        for entry_path, result in self.entries.items():
            entry_pathes = [x for x in entry_path.split('/') if x]
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

    def schedule(self, *args, **kwargs):
        raise Exception("Schedule decorator is defined on BizMicroService, not on TechMicroService")


class MicroServiceProxy:

    def __init__(self, env_name, **kwargs):
        self.session = requests.Session()
        self.cws_id = os.getenv(f'{env_name}_CWS_ID')
        self.cws_token = os.getenv(f'{env_name}_CWS_TOKEN')
        self.cws_stage = os.getenv(f'{env_name}_CWS_STAGE')

        self.session.headers.update(
            {
                'authorization': self.cws_token,
                'content-type': 'application/json',
            })
        self.url = f"https://{self.cws_id}.execute-api.eu-west-1.amazonaws.com/{self.cws_stage}"

    def get(self, path, data=None):
        return self.session.get(f'{self.url}/{path}', data=data)

    def post(self, path, data=None, attachments=None, headers=None, sync=True):
        if headers:
            self.session.headers.update(headers)
        if not sync:
            self.session.headers.update({'InvocationType': 'Event'})
        return self.session.post(f'{self.url}/{path}', json=data or {}, files=attachments)


class BizMicroService(TechMicroService):
    """Biz composed microservice activated by events.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.schedule_entries: Dict[str, ScheduleEntry] = {}
        self.microservices: Dict[str, TechMicroService] = {}

    @property
    def ms_type(self):
        return 'biz'

    def register_microservice(self, service: TechMicroService):
        """ Register a :class:`MicroService` used by the microservice.

        :param service: service to register.
        :return:
        """
        self.microservices[service.name] = service

        @self.before_first_activation
        def first(event, context):
            service.do_before_first_activation(event, context)

        @self.before_activation
        def before(event, context):
            service.do_before_activation(event, context)

        @self.after_activation
        def after(response):
            return service.do_after_activation(response)

        @self.handle_exception
        def after(event, context, e):
            return service.do_handle_exception(event, context, e)

    # noinspection PyMethodOverriding
    def schedule(self, exp, *, name=None, description=None, workspaces=None):
        """Registers a a schedule event to trigger the microservice.

        May be used as a decorator.

        The function will be called with the event name.
        """

        def decorator(f):
            schedule_name = name if name else exp
            desc = description if description else f.__doc__
            entry_key = re.sub(ENTRY_REGEXP, '', exp)
            self.schedule_entries[f"{f.__name__}_{entry_key}"] = ScheduleEntry(schedule_name, exp, desc, f)
            return f

        return decorator

    def handler(self, event, context):
        """Main microservice entry point."""

        if event.get('type') == 'CWS_SCHEDULE_EVENT':
            return self._schedule_event_handler(event, context)
        return super().handler(event, context)

    def _schedule_event_handler(self, event, context):
        """Schedule event handler."""
        self.log.debug(f"Calling {self.name} by event bridge")

        try:
            entry_name = event.get('entry_name')
            return self.schedule_entries[entry_name].fun(event.get('schedule_name'))
        except Exception as e:
            self.log.debug(f"Error in schedule event handler for {self.name} : {e}")
            raise
