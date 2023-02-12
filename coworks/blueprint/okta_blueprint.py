import os

from aws_xray_sdk.core import xray_recorder
from coworks.extension.xray import XRay
from flask import request
from okta.client import Client
from okta.okta_object import OktaObject
from werkzeug.exceptions import InternalServerError

from coworks import Blueprint
from coworks import entry


class OktaClient(Client):
    """Okta client extended to allow next call event on new client defined."""

    @XRay.capture(xray_recorder)
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
    next: Next url to be called if wanted more results.

    OktaRespons are used as global variables from asynchronous functions.

    To set the value from an asynchronous function:
    resp.set(await self.okta_client.function(query_parameters))

    The property response must be used as microservice returned value:
    return resp.response

    To combine results in microservice:
    return OktaResponse.combine({'user': resp_user, 'groups': resp_groups})
    """

    def __init__(self):
        self.api_resp = self.next_url = self.error = None

    @XRay.capture(xray_recorder)
    def set(self, await_result, fields=None):
        """Set the values from the result. Keep only specific fieds if defined."""

        if len(await_result) == 3:
            _, self.api_resp, self.error = await_result
        else:
            self.api_resp, self.error = await_result

        # noinspection PyProtectedMember
        self.next_url = self.api_resp._next if self.api_resp else None

    @property
    def body(self):
        """Get OKTA body response."""
        return self.api_resp.get_body()

    @property
    def response(self):
        """Cast the Okta response as microservice response."""
        if self.error:
            return self.error.message, self.error.status
        return {'value': self.body, 'next': self.next_url}


class Okta(Blueprint):

    def __init__(self, name: str = 'okta',
                 env_url_var_name: str = '', env_token_var_name: str = '',
                 env_var_prefix: str = "OKTA", **kwargs):
        super().__init__(name=name, **kwargs)
        if env_var_prefix:
            self.env_url_var_name = f"{env_var_prefix}_URL"
            self.env_token_var_name = f"{env_var_prefix}_TOKEN"
        else:
            self.env_url_var_name = env_url_var_name
            self.env_token_var_name = env_token_var_name

        self.org_url = os.getenv(self.env_url_var_name)
        if not self.org_url:
            raise InternalServerError(f"Environment var {self.env_url_var_name} undefined.")
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
