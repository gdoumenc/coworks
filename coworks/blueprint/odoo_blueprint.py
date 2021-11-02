import json
import os
from typing import List, Tuple, Union, Any

import requests
from aws_xray_sdk.core import xray_recorder

from .. import Blueprint
from ..error import NotFoundError, InternalServerError, BadRequestError

Response = Tuple[dict, int]
GetResponse = Tuple[Union[dict, List[dict]], int]
Ids = List[int]
Filters = List[Tuple[str, str, Any]]


class AccessDenied(Exception):
    ...


class Odoo(Blueprint):
    """Odoo blueprint.
    This blueprint uses the API Rest application which must be installed on ODOO server.
    Environment variables needed:
    - env_url_var_name: Variable name for the odoo server URL.
    - env_dbname_var_name: Variable name for the odoo database.
    - env_user_var_name: Variable name for the user login.
    - env_passwd_var_name: Variable name for the password.
    """

    def __init__(self, name='odoo',
                 env_url_var_name: str = '', env_dbname_var_name: str = '', env_user_var_name: str = '',
                 env_passwd_var_name: str = '', env_var_prefix: str = '', **kwargs):
        super().__init__(name=name, **kwargs)
        self.url = self.dbname = self.user = self.passwd = None
        self.session_id = None
        if env_var_prefix:
            self.env_url_var_name = f"{env_var_prefix}_URL"
            self.env_dbname_var_name = f"{env_var_prefix}_DBNAME"
            self.env_user_var_name = f"{env_var_prefix}_USER"
            self.env_passwd_var_name = f"{env_var_prefix}_PASSWD"
        else:
            self.env_url_var_name = env_url_var_name
            self.env_dbname_var_name = env_dbname_var_name
            self.env_user_var_name = env_user_var_name
            self.env_passwd_var_name = env_passwd_var_name

        @self.before_app_first_request
        def check_env_vars(event, context):
            self.url = os.getenv(self.env_url_var_name)
            if not self.url:
                raise EnvironmentError(f'{self.env_url_var_name} not defined in environment.')
            self.dbname = os.getenv(self.env_dbname_var_name)
            if not self.dbname:
                raise EnvironmentError(f'{self.env_dbname_var_name} not defined in environment.')
            self.user = os.getenv(self.env_user_var_name)
            if not self.user:
                raise EnvironmentError(f'{self.env_user_var_name} not defined in environment.')
            self.passwd = os.getenv(self.env_passwd_var_name)
            if not self.passwd:
                raise EnvironmentError(f'{self.env_passwd_var_name} not defined in environment.')

        @self.before_app_request
        def set_session(event, context):
            self.session_id, status_code = self._get_session_id()

        @self.after_app_request
        def destroy_session(response):
            self.session_id = self._destroy_session()

    def get(self, model: str, query: str = "{*}", order: str = None, filters: Filters = None,
            limit: int = 300, page_size=None, page=0, ensure_one=False) -> GetResponse:
        """Searches for records based on the args.
        See also: https://www.odoo.com/documentation/14.0/developer/reference/addons/orm.html#odoo.models.Model.search
        @param model: python as a dot separated class name.
        @param query: graphQL notation for result.
        @param order: oder of result.
        @param filters: filter for records.
        @param limit: maximum number of records to return from odoo (default: all).
        @param page_size: pagination done by the microservice.
        @param page: current page searched.
        @param ensure_one: raise error if result is not one (404) and only one (400) object.
        """
        params = {'query': query, 'limit': limit}
        if order:
            params.update({'order': order})
        if filters:
            params.update({'filters': json.dumps(filters)})
        if page_size:
            params.update({'page_size': page_size})
        if page:
            params.update({'page': page})
        res, status_code = self.odoo_get(f'{self.url}/api/{model}', params)
        if status_code == 200:
            if ensure_one:
                if len(res['result']) == 0:
                    raise NotFoundError(f"Nothing found for {model} with {filters} [Odoo blueprint {self.name}]")
                if len(res['result']) > 1:
                    raise BadRequestError("More than one result")
                else:
                    return res['result'][0], 200
            return res['result'], 200
        if status_code == 500:
            raise InternalServerError(f"{res}  [Odoo blueprint {self.name}]")
        return res, status_code

    def get_(self, model: str, rec_id: int, query="{*}") -> Response:
        """Searches for one record based on its id.
        @param model: python as a dot separated class name.
        @param rec_id: id of the record.
        @param query: graphQL notation for result.
        """
        params = {'query': query}
        res, status_code = self.odoo_get(f'{self.url}/api/{model}/{rec_id}', params)
        if status_code == 500:
            raise InternalServerError(f"{res}  [Odoo blueprint {self.name}]")
        return res, status_code

    def get_call(self, model: str):
        return "Not done", 500

    def get_call_(self, model: str, rec_id: int, function, *args, **kwargs) -> Response:
        """Call a class function on a record.
        @param model: python as a dot separated class name.
        @param rec_id: id of the record.
        @param function: name of the function.
        @param args: args for the function call.
        @param kwargs: kwargs for the function call.
        """
        params = {'params': {'args': json.dumps(args) if args else '[]',
                             'kwargs': json.dumps(kwargs) if kwargs else '{}'}}
        res, status_code = self.odoo_post(f"{self.url}/object/{model}/{rec_id}/{function}", params=params)
        if status_code == 200:
            return res['result'], 200
        if status_code == 500:
            raise InternalServerError(f"{res}  [Odoo blueprint {self.name}]")
        return res, status_code

    def get_pdf(self, report_id: int, rec_ids: Ids) -> Response:
        """Returns the PDF document attached to a report.
        @param report_id: id of the record.
        @param rec_ids: records needed to generate the report.
        """
        params = {'params': {'res_ids': json.dumps(rec_ids)}}
        res, status_code = self.odoo_post(f"{self.url}/report/{report_id}", params=params)
        if status_code == 200:
            return res['result'], 200
        if status_code == 500:
            raise InternalServerError(f"{res}  [Odoo blueprint {self.name}]")
        return res, status_code

    def post(self, model: str, data=None, context=None) -> Response:
        """Creates new records for the model..
        See also: https://www.odoo.com/documentation/14.0/developer/reference/addons/orm.html#odoo.models.Model.create
        @param model: python as a dot separated class name.
        @param data: fields to initialize and the value to set on them.
        @param context: fields to initialize and the value to set on them.
        See also: https://www.odoo.com/documentation/14.0/developer/reference/addons/orm.html#odoo.models.Model.with_context
        """
        params = {'params': {'data': data or {}}}
        if context:
            params.update({'context': context})
        res, status_code = self.odoo_post(f"{self.url}/api/{model}", params=params)
        if status_code == 200:
            return res['result'], 200
        if status_code == 500:
            raise InternalServerError(f"{res}  [Odoo blueprint {self.name}]")
        return res, status_code

    def put(self, model: str, rec_id: int, data=None) -> Response:
        """Updates one record with the provided values.
        See also: https://www.odoo.com/documentation/14.0/developer/reference/addons/orm.html#odoo.models.Model.write
        @param model: python as a dot separated class name.
        @param rec_id: id of the record.
        @param data: fields to update and the value to set on them.
        """
        params = {'params': {'data': data or {}}}
        res, status_code = self.odoo_put(f'{self.url}/api/{model}/{rec_id}', params)
        if status_code == 500:
            raise InternalServerError(f"{res}  [Odoo blueprint {self.name}]")
        return res, status_code

    def put_(self, model: str, filters: Filters = None, data=None) -> Response:
        """Updates all records in the current set with the provided values (bulk update).
        See also: https://www.odoo.com/documentation/14.0/developer/reference/addons/orm.html#odoo.models.Model.write
        @param model: python as a dot separated class name.
        @param filters: filter for records.
        @param data: fields to update and the value to set on them.
        """
        params = {'params': {'data': data or {}}}
        if filters:
            params.update({'filter': filters})
        res, status_code = self.odoo_put(f'{self.url}/api/{model}', params)
        if status_code == 500:
            raise InternalServerError(f"{res}  [Odoo blueprint {self.name}]")
        return res, status_code

    def delete(self, model: str, rec_id: int) -> Response:
        """delete the record.
        See also: https://www.odoo.com/documentation/14.0/developer/reference/addons/orm.html#odoo.models.Model.unlink
        @param model: python as a dot separated class name.
        @param rec_id: id of the record.
        """
        res, status_code = self.odoo_delete(f'{self.url}/api/{model}/{rec_id}')
        if status_code == 500:
            raise InternalServerError(f"{res}  [Odoo blueprint {self.name}]")
        return res, status_code

    @xray_recorder.capture()
    def odoo_get(self, path, params, headers=None):
        params.update({'jsonrpc': "2.0", 'session_id': self.session_id})
        headers = headers or {}
        res = requests.get(path, params=params, headers=headers)
        try:
            result = res.json()
            if 'error' in result:
                return f"{result['message']}: {result['data']}", 404
            return result, res.status_code
        except (json.decoder.JSONDecodeError, Exception):
            return res.text, 500

    @xray_recorder.capture()
    def odoo_post(self, path, params, headers=None) -> Tuple[Union[str, dict], int]:
        _params = {'jsonrpc': "2.0", 'session_id': self.session_id}
        headers = headers or {}
        res = requests.post(path, params=_params, json=params, headers=headers)
        try:
            result = res.json()
            if 'error' in result:
                return f"{result['error']['message']}:{result['error']['data']}", 404
            return result, res.status_code
        except (json.decoder.JSONDecodeError, Exception):
            return res.text, 500

    @xray_recorder.capture()
    def odoo_put(self, path, params, headers=None) -> Tuple[Union[str, dict], int]:
        _params = {'jsonrpc': "2.0", 'session_id': self.session_id}
        headers = headers or {}
        res = requests.put(path, params=_params, json=params, headers=headers)
        try:
            result = res.json()
            if 'error' in result:
                return f"{result['error']['message']}:{result['error']['data']}", 404
            return result, res.status_code
        except (json.decoder.JSONDecodeError, Exception):
            return res.text, 500

    @xray_recorder.capture()
    def odoo_delete(self, path, headers=None) -> Tuple[Union[str, dict], int]:
        _params = {'jsonrpc': "2.0", 'session_id': self.session_id}
        headers = headers or {}
        res = requests.delete(path, params=_params, headers=headers)
        try:
            result = res.json()
            if 'error' in result:
                return f"{result['error']['message']}:{result['error']['data']}", 404
            return result, res.status_code
        except (json.decoder.JSONDecodeError, Exception):
            return res.text, 500

    def _get_session_id(self):
        """Open or checks the connection."""
        try:
            data = {
                'jsonrpc': "2.0",
                'params': {
                    'db': self.dbname,
                    'login': self.user,
                    'password': self.passwd,
                }
            }
            res = requests.post(
                f'{self.url}/web/session/authenticate/',
                data=json.dumps(data),
                headers={'Content-type': 'application/json'}
            )

            data = json.loads(res.text)
            if data['result']['session_id']:
                return res.cookies["session_id"], 200
        except Exception as e:
            return str(e), 401

    def _destroy_session(self):
        """Closes the connection."""
        try:
            data = {
                'jsonrpc': "2.0",
                'params': {
                    'db': self.dbname,
                    'login': self.user,
                    'password': self.passwd,
                }
            }
            res = requests.post(
                f'{self.url}/web/session/destroy/',
                data=json.dumps(data),
                headers={'Content-type': 'application/json'}
            )

            return "", 200
        except Exception as e:
            return str(e), 401
