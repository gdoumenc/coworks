import os
from aws_xray_sdk.core import xray_recorder
from okta.client import Client
from typing import Dict

from coworks import Blueprint, entry


class OktaDict(dict):

    def as_dict(self):
        return {k: v for k, v in self.items() if k != "links"}


class OktaClient(Client):

    @xray_recorder.capture()
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
    """Class to manipulate results from okta client.
    value: value returned as dict
    err: Not None if error

    OktaRespons are used as global variables from asynchronous functions.

    To set the value from an asynchronous function:
    resp.set(await self.okta_client.function(query_parameters))

    The property response must be used as microservice returned value:
    return resp.response

    To combine results in microservice:
    return OktaResponse.combine({'user': resp_user, 'groups': resp_groups})
    """

    def __init__(self):
        self.value = self.api_resp = self.err = None

    @xray_recorder.capture()
    def set(self, await_result, fields=None):

        def as_dict(val):
            if fields is None:
                return {k: v for k, v in val.as_dict().items() if not k.startswith('_')}
            return {k: v for k, v in val.as_dict().items() if k in fields}

        if len(await_result) == 3:
            value, self.api_resp, self.err = await_result
            if not self.err:
                self.value = [as_dict(val) for val in value] if type(value) is list else as_dict(value)
        else:
            self.api_resp, self.err = await_result
            self.value = None

    @property
    def response(self):
        """Cast the Okta response as microservice response."""
        if self.err:
            return self.err.message, 400
        if type(self.value) is list:
            return {'value': self.value, 'next': self.api_resp._next}
        return self.value

    def filter(self, fun, map=lambda x: x):
        dest = OktaResponse()
        if not self.err:
            dest.value = [map(val) for val in self.value if fun(val)]
            dest.api_resp = self.api_resp
        else:
            dest.err = self.err
        return dest

    @classmethod
    def combine_response(cls, responses: Dict[str, "OktaResponse"]):
        for resp in responses.values():
            if resp.err:
                return resp.err.message, 400
        return {k: v.response for k, v in responses.items()}


class Okta(Blueprint):

    def __init__(self, env_url_var_name=None, env_token_var_name=None, env_var_prefix="OKTA", **kwargs):
        super().__init__(name='okta', **kwargs)
        self.org_url = self.okta_client = None
        if env_var_prefix:
            self.env_url_var_name = f"{env_var_prefix}_URL"
            self.env_token_var_name = f"{env_var_prefix}_TOKEN"
        else:
            self.env_url_var_name = env_url_var_name
            self.env_token_var_name = env_token_var_name

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
