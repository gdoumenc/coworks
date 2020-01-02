import inspect
import json
import logging
import os
from functools import update_wrapper

import boto3
import sys
from botocore.exceptions import ClientError

from chalice import AuthResponse
from chalice import Chalice, Blueprint as ChaliceBlueprint, ChaliceViewError

from .utils import class_auth_methods, class_rest_methods, class_attribute


class TechMicroService(Chalice):
    """Simple chalice app created directly from class."""

    def __init__(self, config_dir=None, **kwargs):
        app_name = kwargs.pop('app_name', self.__class__.__name__)
        super().__init__(app_name, **kwargs)
        self.experimental_feature_flags.update([
            'BLUEPRINTS'
        ])

        # add root route
        self._add_route(self)

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

    @staticmethod
    def _add_route(component):

        # adds class authorizer for every entries
        auth = class_auth_methods(component)
        if auth:
            auth = TechMicroService._create_auth_proxy(component, auth)
            component.__auth__ = auth

        # adds entrypoints
        methods = class_rest_methods(component)
        for method, func in methods:
            if func.__name__ == method:
                route = f"{component.component_name}"
            else:
                name = func.__name__[len(method) + 1:]
                name = name.replace('_', '/')
                route = f"{component.component_name}/{name}" if component.component_name else f"{name}"
            args = inspect.getfullargspec(func).args[1:]
            defaults = inspect.getfullargspec(func).defaults
            if defaults:
                len_defaults = len(defaults)
                for arg in args[:-len_defaults]:
                    route = route + f"/{{{arg}}}" if route else f"{{{arg}}}"
                kwarg_keys = args[-len_defaults:]
            else:
                for arg in args:
                    route = route + f"/{{{arg}}}" if route else f"{{{arg}}}"
                kwarg_keys = {}

            proxy = TechMicroService._create_rest_proxy(component, func, kwarg_keys)
            component.route(f"/{route}", methods=[method.upper()], authorizer=auth)(proxy)

    @staticmethod
    def _create_auth_proxy(component, auth_method):

        def proxy(auth_request):
            auth = auth_method(component, auth_request)
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
    def _create_rest_proxy(component, func, kwarg_keys):

        def proxy(*args, **kwargs):
            req = component.current_request
            if kwarg_keys:
                if req.query_params:
                    query_params = {}
                    for k in req.query_params:
                        if k not in kwarg_keys:
                            continue
                        value = req.query_params.getlist(k)
                        query_params[k] = value if len(value) > 1 else value[0]
                    kwargs = dict(**kwargs, **query_params)
                if req.json_body:
                    if hasattr(req.json_body, 'items'):
                        kwargs = dict(**kwargs, **{k: v for k, v in req.json_body.items() if k in kwarg_keys})
                    else:
                        kwargs[kwarg_keys[0]] = req.json_body
            return func(component, *args, **kwargs)

        return update_wrapper(proxy, func)

    def __call__(self, event, context):
        if 'type' in event and event['type'] == 'TOKEN':
            return self.__auth__(event, context)
        return super().__call__(event, context)


class BizMicroService(TechMicroService):
    """Chalice app to execute AWS Step Functions."""

    def __init__(self, arn, **kwargs):
        super().__init__(**kwargs)
        self._arn = arn

    def get_describe(self):
        try:
            res = self.client.describe_state_machine(stateMachineArn=self._arn)
            return json.dumps(res, indent=4, sort_keys=True, default=str)
        except ClientError as error:
            raise ChaliceViewError(str(error))

    def get_execution(self, exe_arn):
        try:
            res = self.client.describe_execution(executionArn=exe_arn)
            return json.dumps(res, indent=4, sort_keys=True, default=str)
        except ClientError as error:
            raise ChaliceViewError(str(error))

    def get_last(self, max_results):
        try:
            res = self.client.list_executions(stateMachineArn=self._arn, maxResults=int(max_results))
            return json.dumps(res, indent=4, sort_keys=True, default=str)
        except ClientError as error:
            raise ChaliceViewError(str(error))

    def post_invoke(self):
        try:
            request = self.current_request
            name = request.query_params.get('name', "") if request.query_params else ""
            res = self.client.start_execution(stateMachineArn=self._arn,
                                              input=json.dumps({
                                                  "name": name
                                              }))
            return res['executionArn']
        except ClientError as error:
            raise ChaliceViewError(str(error))

    @property
    def client(self):
        session = boto3.session.Session(profile_name='imprim')
        return session.client('stepfunctions')


class Blueprint(ChaliceBlueprint):
    """Chalice blueprint created directly from class."""

    def __init__(self, **kwargs):
        import_name = kwargs.pop('import_name', self.__class__.__name__)
        super().__init__(import_name)

    @property
    def component_name(self):
        return ''


