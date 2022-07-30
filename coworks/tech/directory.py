import os
import re

import boto3
import requests
from aws_xray_sdk.core import xray_recorder
from flask import current_app
from werkzeug.exceptions import BadRequest
from werkzeug.exceptions import MethodNotAllowed
from werkzeug.exceptions import NotFound

from coworks import TechMicroService
from coworks import entry
from coworks.blueprint.admin_blueprint import Admin
from coworks.middleware.xray import XRayMiddleware
from coworks.utils import is_json


class DirectoryMicroService(TechMicroService):
    DOC_MD = """
## Directory service

Microservice to get information on or call a CoWorks TechMicroServices deployed.
See samples/directory to get how to create and deploy it.

#### Find a microservice by a regular expression

``` python
data = {
  "pattern":".*directory.*",
  "position": ""
}
requests.post('/', json=data)
```

#### Get documentation

``` python
requests.get('/doc/{name}')
```

#### Get all stages defined

``` python
requests.get('/stages/{name}')
```
"""

    def __init__(self, **kwargs):
        super().__init__(name="directory", **kwargs)
        self.register_blueprint(Admin(), url_prefix='admin')
        XRayMiddleware(self, xray_recorder)
        self.api_client = self.lambda_client = None
        self.access_key = None

    def init_app(self):
        self.access_key = os.getenv("AWS_USER_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_USER_SECRET_ACCESS_KEY")
        region_name = os.getenv("AWS_REGION_NAME")
        session = boto3.Session(self.access_key, secret_key, region_name=region_name)
        self.api_client = session.client('apigateway')
        self.lambda_client = session.client('lambda')

    @entry
    def post(self, pattern=None, position=None):
        """Get the list of microservices which matchs the 'pattern'.
        Pagination done by 'position'.
        """
        try:
            match_re = re.compile(pattern) if pattern else None
        except re.error as e:
            raise BadRequest(f"Wrong regular expression: {e.msg}")

        def found(a):
            return match_re.search(a['name']) if match_re else True

        boto3_args = {'limit': 100}
        if position:
            boto3_args.update({'position': position})
        try:
            objects = self.api_client.get_rest_apis(**boto3_args)
        except (Exception,) as e:
            raise BadRequest(e.msg)
        api = [*filter(found, objects['items'])]
        position = self._get_position(objects)
        while position and len(api) < 500:
            objects = self.api_client.get_rest_apis(position=position, limit=100)
            api = [*api, *filter(found, objects['items'])]
            position = self._get_position(objects)

        return {
            'items': {a['name']: a['id'] for a in api},
            'position': position if position else ''
        }

    @entry
    def get_aws(self, name):
        """Get AWS information on the microservice whith name 'name'.

        :param name: Microservice name.
        """

        def found(apis):
            for a in apis:
                if a['name'] == name:
                    return a

        objects = self.api_client.get_rest_apis(limit=100)
        api = found(objects['items'])
        if api:
            return api
        position = objects['position']
        while position:
            objects = self.api_client.get_rest_apis(position=position, limit=100)
            api = found(objects['items'])
            if api:
                return api
            position = objects['position'] if 'position' in objects else None

        raise NotFound()

    @entry
    def get_stages(self, name):
        """Get microservice stages for the microservice whith name 'name'.
        """
        api = self.get_aws(name)
        api_id = api['id']
        stages = self.api_client.get_stages(restApiId=api_id)
        return {s['stageName']: {**s, 'api_id': api_id} for s in stages['item']}

    @entry
    def get_url(self, name, stage=None, token_var_name='TOKEN'):
        """Get microservice url for the microservice whith name 'name'.
        If stage is not defined the latest production version is choosen or 'dev' if no production version.
        """
        api_id = ""
        stages = self.get_stages(name)
        if stage:
            if stage not in stages:
                raise NotFound()
        else:
            stage = sorted(stages)[-1]
        api_id = stages[stage]['api_id']

        auths = self.api_client.get_authorizers(restApiId=api_id)
        lambda_uri = auths['items'][0]['authorizerUri']
        uris = lambda_uri.split(':')
        lambda_name = f"{uris[-1].split('$')[0]}{stage}"
        lambda_fun = self.lambda_client.get_function(FunctionName=lambda_name)
        token = lambda_fun['Configuration']['Environment']['Variables'][token_var_name]

        url = f"https://{api_id}.execute-api.eu-west-1.amazonaws.com/{stage}"
        result = {'url': url, 'token': token}
        xray_recorder.put_metadata('return', result, namespace='coworks')
        return result

    @entry
    def get_doc(self, name, stage=None, token_var_name='TOKEN', **data):
        """Get microservice documentation.
        If stage is not defined the latest production version is choosen or 'dev' if no production version.
        """
        info = self.get_url(name, stage=stage, token_var_name=token_var_name)
        headers = {
            'Authorization': info['token'],
            'Content-Type': 'application/json',
            'Accept': 'text/html; charset utf-8',
        }
        url = f"{info['url']}/admin"
        res = requests.get(url, headers=headers)
        return res.text, res.status_code, dict(res.headers)

    @entry
    def post_call(self, name, stage=None, path='/admin', method='get', token_var_name='TOKEN',
                  accept='application/json', data=None):
        """Call a microservice from its name.
        :param name: microservice's name.
        :param stage: method called.
        If stage is not defined the latest production version is choosen or 'dev' if no production version.
        :param path: entry path (default '/admin').
        :param method: method called (default 'get').
        :param token_var_name: token variable name (default 'TOKEN').
        :param accept: header accpt value (default 'application/json').
        :param data: query parameters or json body (default {}).
        """
        data = data or {}
        info = self.get_url(name, stage=stage, token_var_name=token_var_name)
        headers = {
            'Authorization': info['token'],
            'Content-Type': 'application/json',
            'Accept': accept,
        }
        url = f"{info['url']}{path}"

        current_app.logger.info(f"{method.upper()} on {url}, with {data}")
        if method.upper() == 'GET':
            res = requests.get(url, params=data, headers=headers)
        elif method.upper() == 'POST':
            res = requests.post(url, json=data, headers=headers)
        else:
            raise MethodNotAllowed()

        return res.json() if is_json(accept) else res.text, res.status_code, dict(res.headers)

    @entry
    def get_api(self, api_id):
        """Get microservice name from 'api_id'.
        """
        return self.api_client.get_rest_api(restApiId=api_id)

    def _get_position(self, objects):
        return objects['position'] if 'position' in objects else None


app = DirectoryMicroService()
