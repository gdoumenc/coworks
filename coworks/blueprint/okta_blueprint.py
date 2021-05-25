import os
from okta.client import Client
from typing import Dict

from coworks import Blueprint, entry


class OktaDict(dict):

    def as_dict(self):
        return {k: v for k, v in self.items() if k != "links"}


class OktaClient(Client):

    async def next(self, next):
        request, error = await self._request_executor.create_request("GET", next, {}, {})
        if error:
            return None, None, error
        response, error = await self._request_executor.execute(request)
        if error:
            return None, None, error
        result = []
        for item in response.get_body():
            obj = self.form_response_body(item)
            result.append(OktaDict(**obj))
        return result, response, error


class OktaResponse:

    def __init__(self):
        self.value = self.api_resp = self.err = None

    def set(self, await_result, fields=None):

        def as_dict(val):
            if fields is None:
                return {k: v for k, v in val.as_dict().items() if not k.startswith('_')}
            return {k: v for k, v in val.as_dict().items() if k in fields}

        value, self.api_resp, self.err = await_result
        self.value = [as_dict(val) for val in value] if type(value) is list else as_dict(value)

    def extract(self, dest, fun):
        dest.api_resp = self.api_resp
        dest.err = self.err
        if not self.err:
            dest.value = [val for val in self.value if fun(val)]
            self.value = [val for val in self.value if not fun(val)]

    @property
    def response(self):
        if self.err:
            return self.value, self.err
        if type(self.value) is list:
            return {'value': self.value, 'next': self.api_resp._next}
        return self.value

    @classmethod
    def combine(cls, responses: Dict[str, "OktaResponse"]):
        for resp in responses.values():
            if resp.err:
                return resp.err.message, 400
        return {k: v.response for k, v in responses.items()}


class Okta(Blueprint):

    def __init__(self, env_url_var_name=None, env_token_var_name=None, env_var_prefix="OKTA", **kwargs):
        super().__init__(name='okta', **kwargs)
        if env_var_prefix:
            self.env_url_var_name = f"{env_var_prefix}_URL"
            self.env_token_var_name = f"{env_var_prefix}_TOKEN"
        else:
            self.env_url_var_name = env_url_var_name
            self.env_token_var_name = env_token_var_name
        self.org_url = self.okta_client = None

        @self.before_first_activation
        def client(event, context):
            self.org_url = os.getenv(self.env_url_var_name)
            assert self.org_url, f"Environment var {self.env_url_var_name} undefined."
            config = {
                'orgUrl': self.org_url,
                'token': os.getenv(self.env_token_var_name)
            }
            self.okta_client = OktaClient(config)

    @entry
    def get_event_verify(self):
        test_value = self.current_request.headers.get('x-okta-verification-challenge')
        return {"verification": test_value}
