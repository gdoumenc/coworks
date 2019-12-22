import inspect
import json
import logging
import os
import sys
from collections import defaultdict
from functools import update_wrapper, partial

import boto3
from botocore.exceptions import ClientError
from chalice import Chalice, Blueprint as ChaliceBlueprint, NotFoundError, ChaliceViewError

from .utils import class_rest_methods, class_attribute


class TechMicroService(Chalice):

    def __init__(self, **kwargs):
        app_name = kwargs.pop('app_name', self.__class__.__name__)
        super().__init__(app_name, **kwargs)
        self.experimental_feature_flags.update([
            'BLUEPRINTS'
        ])

        # add root route
        self._add_route()

    def register_blueprint(self, blueprint, **kwargs):
        slug = class_attribute(blueprint, 'slug', '')
        self._add_route(blueprint)
        if 'name_prefix' not in kwargs:
            kwargs['name_prefix'] = blueprint.import_name
        if not slug and 'url_prefix' not in kwargs:
            kwargs['url_prefix'] = f"/{blueprint.import_name}"
        super().register_blueprint(blueprint, **kwargs)

    def run(self, host='127.0.0.1', port=8000, stage=None, debug=True, profile=None):
        # TODO missing test
        from chalice.cli import CLIFactory, run_local_server
        from chalice.cli import DEFAULT_STAGE_NAME
        stage = stage or DEFAULT_STAGE_NAME

        class CWSFactory(CLIFactory):
            def __init__(self, app, project_dir, environ=None):
                self.app = app
                super().__init__(project_dir, debug=debug, profile=profile, environ=environ)

            def load_chalice_app(self, environment_variables=None, **kwargs):
                if environment_variables is not None:
                    self._environ.update(environment_variables)
                    for key, val in self._environ.items():
                        os.environ[key] = val
                return self.app

        factory = CWSFactory(self, '.')
        logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')
        run_local_server(factory, host, port, stage)

    def _add_route(self, component=None):
        component = component if component else self
        slug = class_attribute(component, 'slug', '')
        methods = class_rest_methods(component)
        for method, func in methods:
            if func.__name__ == method:
                route = f"{slug}"
            else:
                name = func.__name__[len(method) + 1:]
                route = f"{slug}/{name}" if slug else f"{name}"
            args = inspect.getfullargspec(func).args[1:]
            for arg in args:
                route = route + f"/{{{arg}}}" if route else f"{{{arg}}}"

            proxy = update_wrapper(partial(func, component), func)
            component.route(f"/{route}", methods=[method.upper()])(proxy)


class BizMicroService(TechMicroService):

    def __init__(self, arn, **kwargs):
        super().__init__(arn, **kwargs)
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

    def get_last(self, max):
        try:
            res = self.client.list_executions(stateMachineArn=self._arn, maxResults=int(max))
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


class BizMicroServiceManager(TechMicroService):
    sfns = defaultdict(dict)

    def get(self):
        try:
            res = self.client.list_state_machines(maxResults=100)
            for m in res['stateMachines']:
                BizMicroService.sfns[m['name']] = m
            return len(BizMicroService.sfns)
        except ClientError as error:
            return ChaliceViewError(str(error))

    def get_list(self):
        self.get()
        return [{'name': m['name'], 'arn': m['stateMachineArn']} for m in BizMicroService.sfns.values()]

    def get_arn(self, name):
        self.get()
        res = BizMicroService.sfns.get(name)
        return res['arn'] if res else NotFoundError

    def get_status(self, name):
        sfn = BizMicroService.sfns.get(name)
        if sfn:
            return sfn
        try:
            res = self.client.describe_state_machine(stateMachineArn=name)
            status = res['status']
            BizMicroService.sfns[name] = status
            return status
        except ClientError as error:
            code = error.response['Error']['Code']
            if code == 'InvalidArn':
                return NotFoundError()
            return ChaliceViewError(str(error))


class Blueprint(ChaliceBlueprint):

    @property
    def import_name(self):
        return self._import_name
