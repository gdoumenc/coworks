import os
from urllib.parse import urljoin

import requests


class MicroServiceProxy:

    def __init__(self, env_name, config=None):
        """Proxy class to access deployed CoWorks microservice.
        Get id, token and stage from environment name
        :param env_name: if XX then XXX_CWS_ID for id, XXX_CWS_TOKEN for token and XXX_CWS_STAGE for stage.
        :param config: if defined must be dict like variable to retrieve id, token and stage.
        """
        self.session = requests.Session()

        if config is not None:
            if hasattr(config, 'get'):
                self.cws_id = config.get(f'{env_name}_CWS_ID')
                self.cws_token = config.get(f'{env_name}_CWS_TOKEN')
                self.cws_stage = config.get(f'{env_name}_CWS_STAGE', 'dev')
            else:
                self.cws_id = getattr(config, f'{env_name}_CWS_ID')
                self.cws_token = getattr(config, f'{env_name}_CWS_TOKEN')
                self.cws_stage = getattr(config, f'{env_name}_CWS_STAGE', 'dev')
        else:
            self.cws_id = os.getenv(f'{env_name}_CWS_ID')
            self.cws_token = os.getenv(f'{env_name}_CWS_TOKEN')
            self.cws_stage = os.getenv(f'{env_name}_CWS_STAGE', 'dev')

        if not self.cws_id:
            raise EnvironmentError(f"Environment variable {env_name}_CWS_ID not defined")
        if not self.cws_token:
            raise EnvironmentError(f"Environment variable {env_name}_CWS_TOKEN not defined")

        self.session.headers.update({
            'authorization': self.cws_token,
            'content-type': 'application/json',
        })
        self.url = f"https://{self.cws_id}.execute-api.eu-west-1.amazonaws.com/{self.cws_stage}/"

    def get(self, path, params=None, response_content_type='json'):
        if path.startswith('/'):
            path = path[1:]
        resp = self.session.get(urljoin(self.url, path), params=params)
        return self.convert(resp, response_content_type)

    # noinspection PyShadowingNames
    def post(self, path, json=None, headers=None, sync=True, response_content_type='json'):
        if path.startswith('/'):
            path = path[1:]
        headers = {**self.session.headers, **headers} if headers else self.session.headers
        if not sync:
            headers.update({'InvocationType': 'Event'})
        resp = self.session.post(urljoin(self.url, path), json=json or {}, headers=headers)
        return self.convert(resp, response_content_type)

    def put(self, path, json=None, headers=None, sync=True, response_content_type='json'):
        if path.startswith('/'):
            path = path[1:]
        headers = {**self.session.headers, **headers} if headers else self.session.headers
        if not sync:
            headers.update({'InvocationType': 'Event'})
        resp = self.session.put(urljoin(self.url, path), json=json or {}, headers=headers)
        return self.convert(resp, response_content_type)

    @property
    def routes(self):
        return self.get('/admin/route')

    @staticmethod
    def convert(resp, response_content_type):
        if resp.status_code == 200:
            if response_content_type == 'text':
                content = resp.text
            elif response_content_type == 'json':
                content = resp.json()
            else:
                content = resp.content
        else:
            content = resp.text or resp.reason
        return content, resp.status_code
