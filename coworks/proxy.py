import os
import requests
from urllib.parse import urljoin


class MicroServiceProxy:

    def __init__(self, env_name, **kwargs):
        self.session = requests.Session()
        self.cws_id = os.getenv(f'{env_name}_CWS_ID')
        self.cws_token = os.getenv(f'{env_name}_CWS_TOKEN')
        self.cws_stage = os.getenv(f'{env_name}_CWS_STAGE')

        self.session.headers.update({
            'authorization': self.cws_token,
            'content-type': 'application/json',
        })
        self.url = f"https://{self.cws_id}.execute-api.eu-west-1.amazonaws.com/{self.cws_stage}/"

    def get(self, path, data=None, response_content_type='json'):
        resp = self.session.get(urljoin(self.url, path), data=data)
        return self.convert(resp, response_content_type)

    # noinspection PyShadowingNames
    def post(self, path, data=None, json=None, headers=None, sync=True, response_content_type='json'):
        headers = {**self.session.headers, **headers} if headers else self.session.headers
        if not sync:
            headers.update({'InvocationType': 'Event'})
        resp = self.session.post(urljoin(self.url, path), data=data, json=json or {}, headers=headers)
        return self.convert(resp, response_content_type)

    @staticmethod
    def convert(resp, response_content_type):
        resp.raise_for_status()
        if response_content_type == 'text':
            content = resp.text
        elif response_content_type == 'json':
            content = resp.json()
        else:
            content = resp.content
        return content, resp.status_code
