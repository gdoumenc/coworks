from dataclasses import dataclass

import os
import typing as t
from abc import ABCMeta
from flask import Blueprint as FlaskBlueprint, Flask, Response, current_app
from flask.ctx import AppContext as FlaskAppContext
from functools import partial

from .config import Config, DEFAULT_WORKSPACE, DevConfig, LocalConfig, ProdConfig
from .mixins import CoworksMixin
from .testing import CoworksClient
from .utils import HTTP_METHODS, trim_underscores

ENTRY_REGEXP = '[^0-9a-zA-Z_]'


#
# Decorators
#

def entry(fun):
    """Decorator to create a microservice entry point from function name."""
    name = fun.__name__.upper()
    for method in HTTP_METHODS:
        fun.__CWS_METHOD = method
        if name == method:
            fun.__CWS_PATH = ''
            return fun
        if name.startswith(f'{method}_'):
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

class AppCtx(FlaskAppContext):
    """Coworks application context."""

    def push(self) -> None:
        super().push()

        # Must be done only once the application context is pushed (for global current app)
        app = t.cast(TechMicroService, self.app)
        app.deferred_init()


@dataclass
class ScheduleEntry:
    """An schedule entry is an EventBridge entry defined on a microservice, with the schedule expression,
    its description and its response function."""

    name: str
    exp: str
    desc: str
    fun: t.Callable


class CoworksResponse(Response):
    default_mimetype = "application/json"

    @property
    def text(self):
        return self.get_data(as_text=True)


class Blueprint(CoworksMixin, FlaskBlueprint, metaclass=ABCMeta):
    """ Represents a blueprint, list of routes that will be added to microservice when registered.

    See :ref:`Blueprint <blueprint>` for more information.
    """

    def __init__(self, name=None, **kwargs):
        """Initialize a blueprint.

        :param kwargs: Other Flask blueprint parameters.

        """
        import_name = self.__class__.__name__.lower()
        super().__init__(name or import_name, import_name)
        self.deferred_init_functions: t.List[t.Callable] = []

    @property
    def logger(self):
        return current_app.logger

    def make_setup_state(self, app, options, *args):
        """Stores creation state for deferred initialization."""
        state = super().make_setup_state(app, options, *args)

        # Defer blueprint route initialization.
        if not options.get('hide_routes', False):
            self.deferred_init_functions.append(partial(self.init_routes, state))

        return state

    def deferred_init(self):
        for fun in self.deferred_init_functions:
            fun()

    # def context_manager(self, name, *args, **kwarsg):
    #     return self.current_app.context_manager(name, *args, **kwarsg)


class ContextManager(metaclass=ABCMeta):
    """ Represents a context manager that will be added to microservice when created.

    See :ref:`ContextManager <contextmanager>` for more information.
    """

    # def __init__(self, app, name):
    #     app.add_context_manager(self, name)
    #     self._current_app = app
    #
    # @abstractmethod
    # def __call__(self, *args, **kwargs):
    #     ...


class TechMicroService(CoworksMixin, Flask):
    """Simple tech microservice.
    
    See :ref:`tech` for more information.
    """

    def __init__(self, name=None, *, configs=None, **kwargs):
        """ Initialize a technical microservice.
        :param name: Name used to identify the microservice.
        :param configs: Deployment configurations.
        :param kwargs: Other Chalice parameters.
        """
        name = name or self.__class__.__name__.lower()

        self.configs = configs or [LocalConfig(), DevConfig(), ProdConfig()]
        if type(self.configs) is not list:
            self.configs = [configs]

        super().__init__(import_name=name, static_folder=None, **kwargs)

        self.response_class = CoworksResponse
        self.test_client_class = CoworksClient

        self._coworks_initialized = False

    def deferred_init(self):
        """Deferred initialization.
        Python initialization is done on module loading, this initialization is done on first use.
        """
        if not self._coworks_initialized:
            workspace = os.environ.get('WORKSPACE', DEFAULT_WORKSPACE)
            config = self.get_config(workspace)
            self.config.update(config.asdict())

            # Initializes routes and deferred initializations
            self.init_routes(self)
            for bp in self.blueprints.values():
                t.cast(Blueprint, bp).deferred_init()
            self._coworks_initialized = True

    def app_context(self):
        """Override to return CoWorks application context."""
        return AppCtx(self)

    @property
    def ms_type(self):
        return 'tech'

    @property
    def routes(self):
        """Returns the list of routes defined in the microservice."""
        return [r.rule for r in self.url_map.iter_rules()]

    def get_config(self, workspace):
        for conf in self.configs:
            if conf.is_valid_for(workspace):
                return conf
        return Config()

    # @contextmanager
    # def context_manager(self, name, *args, **kwargs):
    #     try:
    #         with self.context_managers[name](*args, **kwargs) as cm:
    #             yield cm
    #     except KeyError:
    #         self.log.error(f"Undefined context manager {name}")
    #         raise

    # def add_context_manager(self, context_manager: ContextManager, name: str) -> None:
    #     """ Register a context manager.
    #
    #     :param context_manager: context manager to register.
    #     :param name: name registration (needed to retrieve it).
    #     """
    #     if name in self.context_managers:
    #         raise KeyError(f"A context manager is already defined with the name : {name}.")
    #
    #     self.context_managers[name] = context_manager
    #

    def __call__(self, arg1, arg2):
        """Lambda handler."""
        buffer: t.List[bytes] = []

        def start_response(status, headers, exc_info=None):  # type: ignore
            nonlocal response

            if exc_info:
                try:
                    raise exc_info[1].with_traceback(exc_info[2])
                finally:
                    exc_info = None

            response = (status, headers)
            return buffer.append

        if type(arg2) is dict:
            wsgi_environ = self._create_environ_from_event_and_context(arg1, arg2)
            response = self.handler(wsgi_environ, start_response)
        else:
            response = self.handler(arg1, arg2)
        return response

    def handler(self, eviron, start_response):
        """Main microservice entry point."""

        if eviron.get('type') == 'TOKEN':
            return self._token_handler(eviron, start_response)
        return self._api_handler(eviron, start_response)

    def _token_handler(self, event, context):
        """Authorization handler."""
        self.logger.debug(f"Calling {self.name} for authorization : {event}")

        try:
            *_, method, route = event.get('methodArn').split('/', 3)
            authorizer = self._entry(f'/{route}', method).auth
            return authorizer(event, context)
        except Exception as e:
            self.logger.debug(f"Error in authorization handler for {self.name} : {e}")
            request = AuthRequest(event['type'], event['authorizationToken'], event['methodArn'])
            return AuthResponse(routes=[], principal_id='user').to_dict(request)

    def _api_handler(self, environ, start_response):
        """API rest handler."""
        self.logger.debug(f"Calling {self.name} by api : {environ}")

        try:
            # Chalice accepts only proxy integration and string for body
            self._complete_for_proxy(environ, start_response)

            res = super().__call__(environ, start_response)
            workspace = os.getenv('WORKSPACE')
            if workspace:
                res['headers']['x-cws-workspace'] = workspace

            self.logger.debug(f"Call {self.name} returns {res}")
            return res
        except Exception as e:
            self.logger.debug(f"Error in api handler for {self.name} : {e}")
            raise

    @staticmethod
    def _create_environ_from_event_and_context(event, context) -> dict:
        environ = {
            '"HTTP_HOST"': "",
        }
        return environ

    @staticmethod
    def _complete_for_proxy(event, context):
        request_context = event.get('requestContext')
        # if 'resourcePath' not in request_context:
        #
        #     # Creates proxy routes and path parameters
        #     entry_path = request_context.get('entryPath')
        #     entry_path_parameters = event.get('entryPathParameters')
        #     proxy_resource_path = []
        #     proxy_path_parameters = {}
        #     counter = 0
        #     for subpath in entry_path.split('/'):
        #         if subpath.startswith('{'):
        #             proxy_resource_path.append(f'{{_{counter}}}')
        #             proxy_path_parameters[f'_{counter}'] = entry_path_parameters.get(subpath[1:-1])
        #             counter = counter + 1
        #         else:
        #             proxy_resource_path.append(subpath)
        #
        #     # Completes the event with proxy parameters
        #     request_context['resourcePath'] = '/'.join(proxy_resource_path)
        #     event['pathParameters'] = proxy_path_parameters
        #
        # if type(event['body']) is dict:
        #     event['body'] = json.dumps(event['body'])

    def schedule(self, *args, **kwargs):
        raise Exception("Schedule decorator is defined on BizMicroService, not on TechMicroService")


class BizMicroService(TechMicroService):
    """Biz composed microservice activated by events.
    """

    # def __init__(self, **kwargs):
    #     super().__init__(**kwargs)
    #     self.schedule_entries: Dict[str, ScheduleEntry] = {}
    #     self.microservices: Dict[str, TechMicroService] = {}
    #
    # @property
    # def ms_type(self):
    #     return 'biz'
    #
    # def register_microservice(self, service: TechMicroService):
    #     """ Register a :class:`MicroService` used by the microservice.
    #
    #     :param service: service to register.
    #     :return:
    #     """
    #     self.microservices[service.name] = service
    #
    #     @self.before_first_activation
    #     def first(event, context):
    #         service.do_before_first_activation(event, context)
    #
    #     @self.before_activation
    #     def before(event, context):
    #         service.do_before_activation(event, context)
    #
    #     @self.after_activation
    #     def after(response):
    #         return service.do_after_activation(response)
    #
    #     @self.handle_exception
    #     def after(event, context, e):
    #         return service.do_handle_exception(event, context, e)
    #
    # # noinspection PyMethodOverriding
    # def schedule(self, exp, *, name=None, description=None, workspaces=None):
    #     """Registers a a schedule event to trigger the microservice.
    #
    #     May be used as a decorator.
    #
    #     The function will be called with the event name.
    #     """
    #
    #     def decorator(f):
    #         schedule_name = name if name else exp
    #         desc = description if description else f.__doc__
    #         entry_key = re.sub(ENTRY_REGEXP, '', exp)
    #         self.schedule_entries[f"{f.__name__}_{entry_key}"] = ScheduleEntry(schedule_name, exp, desc, f)
    #         return f
    #
    #     return decorator
    #
    # def handler(self, event, context):
    #     """Main microservice entry point."""
    #
    #     if event.get('type') == 'CWS_SCHEDULE_EVENT':
    #         return self._schedule_event_handler(event, context)
    #     return super().handler(event, context)
    #
    # def _schedule_event_handler(self, event, context):
    #     """Schedule event handler."""
    #     self.log.debug(f"Calling {self.name} by event bridge")
    #
    #     try:
    #         entry_name = event.get('entry_name')
    #         return self.schedule_entries[entry_name].fun(event.get('schedule_name'))
    #     except Exception as e:
    #         self.log.debug(f"Error in schedule event handler for {self.name} : {e}")
    #         raise
