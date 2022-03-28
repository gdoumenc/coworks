import os
from typing import Callable

from aws_xray_sdk.core import xray_recorder
from flask import request
from okta.api_response import OktaAPIResponse as APIResponse
from okta.client import Client
from okta.okta_object import OktaObject

from coworks import Blueprint
from coworks import entry


class OktaClient(Client):
    """Okta client extended to allow next call event on new client defined."""

    @xray_recorder.capture()
    async def next(self, next):
        req, error = await self._request_executor.create_request("GET", next, {}, {})
        if error:
            return None, error
        response, error = await self._request_executor.execute(req)
        try:
            result = []
            for item in response.get_body():
                result.append(OktaDict(self.form_response_body(item)))
        except Exception as error:
            return None, error
        return result, response, None


class OktaResponse:
    """Class to manipulate results from okta client.
    value: value returned as a list of dict.
    err: Not None if error.
    next: Next url to be called if wanted nmore results.

    OktaRespons are used as global variables from asynchronous functions.

    To set the value from an asynchronous function:
    resp.set(await self.okta_client.function(query_parameters))

    The property response must be used as microservice returned value:
    return resp.response

    To combine results in microservice:
    return OktaResponse.combine({'user': resp_user, 'groups': resp_groups})
    """

    def __init__(self, value=None):
        self.value = value
        self.api_resp = self.next_url = self.error = None

    @xray_recorder.capture()
    def set(self, await_result, fields=None):
        """Set the values from the result. Keep only specific fieds if defined."""

        def as_dict(val):
            """Get only specific fields or not protected."""
            if fields is None:
                return {k: v for k, v in val.as_dict().items() if not k.startswith('_')}
            return {k: v for k, v in val.as_dict().items() if k in fields}

        if len(await_result) == 3:
            value, self.api_resp, self.error = await_result
            if not self.error:
                self.value = [as_dict(val) for val in value] if type(value) is list else [as_dict(value)]
            else:
                self.value = []
        else:
            self.api_resp, self.error = await_result
            self.value = []

        self.next_url = next_url(self.api_resp)

    @staticmethod
    def empty_value():
        empty = OktaResponse()
        empty.value = []
        return empty

    @property
    def body(self):
        """Get OKTA body response."""
        return self.api_resp.get_body()

    @property
    def response(self):
        """Cast the Okta response as microservice response."""
        if self.error:
            return self.error.message.decode('utf-8'), self.error.status
        return {'value': self.value, 'next': self.next_url}

    def filter(self, fun: Callable[[dict], bool], map=lambda x: x):
        """Filters the response by the fun parameters and apply map on each."""
        dest = OktaResponse()
        if not self.error:
            dest.value = [map(val) for val in self.value if fun(val)]
            dest.next_url = self.next_url
        else:
            dest.error = self.error
        return dest

    def reduce(self, key):
        """Reduces the response with same key value."""
        dest = OktaResponse()
        if not self.error:
            dest.value = [v for v in {t[key]: t for t in self.value}.values()]
            dest.next_url = self.next_url
        else:
            dest.error = self.error
        return dest


class Okta(Blueprint):

    def __init__(self, name: str = 'okta',
                 env_url_var_name: str = '', env_token_var_name: str = '',
                 env_var_prefix: str = "OKTA", **kwargs):
        super().__init__(name=name, **kwargs)
        self.org_url = self.okta_client = None
        if env_var_prefix:
            self.env_url_var_name = f"{env_var_prefix}_URL"
            self.env_token_var_name = f"{env_var_prefix}_TOKEN"
        else:
            self.env_url_var_name = env_url_var_name
            self.env_token_var_name = env_token_var_name

    def init_app(self, app):
        self.org_url = os.getenv(self.env_url_var_name)
        assert self.org_url, f"Environment var {self.env_url_var_name} undefined."
        config = {
            'orgUrl': self.org_url,
            'token': os.getenv(self.env_token_var_name)
        }
        self.okta_client = OktaClient(config)

    @entry
    def get_event_verify(self):
        """Entry for Okta webhook verification."""
        test_value = request.headers.get('x-okta-verification-challenge')
        return {"verification": test_value}


class OktaDict(OktaObject):
    """Simplified generic okta object."""

    def __init__(self, values):
        super().__init__()
        self.values = values

    def as_dict(self):
        return {k: v for k, v in self.values.items() if k != "links"}


def next_url(resp: APIResponse):
    """Function to access protected next parameter without complain."""
    # noinspection PyProtectedMember
    return resp._next if resp else ""
