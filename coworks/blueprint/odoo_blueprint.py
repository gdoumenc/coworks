import json
import os
import requests
from aws_xray_sdk.core import xray_recorder
from typing import List, Tuple, Union, Any

from .. import Blueprint, entry
from ..error import NotFoundError, InternalServerError

Response = Tuple[dict, int]
GetResponse = Tuple[Union[dict, List[dict]], int]
Ids = List[int]
Filters = List[Tuple[str, str, Any]]


class AccessDenied(Exception):
    ...


class Odoo(Blueprint):
    """Odoo blueprint.
    Environment variables needed:
    - env_url_var_name: Variable name for the odoo server URL.
    - env_dbname_var_name: Variable name for the odoo database.
    - env_user_var_name: Variable name for the user login.
    - env_passwd_var_name: Variable name for the password.
    """

    def __init__(self,
                 env_url_var_name=None, env_dbname_var_name=None, env_user_var_name=None, env_passwd_var_name=None,
                 env_var_prefix=None, **kwargs):
        super().__init__(**kwargs)
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
        self.url = self.dbname = self.user = self.passwd = None
        self.session_id = None

        @self.before_first_activation
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

        @self.before_activation
        def set_session(event, context):
            self.session_id, status_code = self._get_session_id()

        @self.after_activation
        def destroy_session(response):
            self.session_id = self._destroy_session()

        @self.handle_exception
        def handle_access_denied(event, context, e):
            if type(e) is AccessDenied:
                return "AccessDenied", 401
            raise

    @entry
    def get(self, model: str, query: str = "{*}", order: str = None, filters: Filters = None,
            limit: int = 300, page_size=None, page=0, ensure_one=False) -> GetResponse:
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
                    raise InternalServerError("More than one result")
                else:
                    return res['result'][0], 200
            return res['result'], 200
        if status_code == 500:
            raise InternalServerError(f"{res}  [Odoo blueprint {self.name}]")
        return res, status_code

    @entry
    def get_(self, model: str, rec_id: int, query="{*}") -> Response:
        params = {'query': query}
        res, status_code = self.odoo_get(f'{self.url}/api/{model}/{rec_id}', params)
        if status_code == 500:
            raise InternalServerError(f"{res}  [Odoo blueprint {self.name}]")
        return res, status_code

    @entry
    def get_call(self, model: str):
        return "Not done", 500

    @entry
    def get_call_(self, model: str, rec_id: int, function, *args, **kwargs) -> Response:
        params = {'params': {'args': json.dumps(args) if args else '[]',
                             'kwargs': json.dumps(kwargs) if kwargs else '{}'}}
        res, status_code = self.odoo_post(f"{self.url}/object/{model}/{rec_id}/{function}", params=params)
        if status_code == 200:
            return res['result'], 200
        if status_code == 500:
            raise InternalServerError(f"{res}  [Odoo blueprint {self.name}]")
        return res, status_code

    @entry
    def get_pdf(self, report_id: int, rec_ids: Ids) -> Response:
        params = {'params': {'res_ids': json.dumps(rec_ids)}}
        res, status_code = self.odoo_post(f"{self.url}/report/{report_id}", params=params)
        if status_code == 200:
            return res['result'], 200
        if status_code == 500:
            raise InternalServerError(f"{res}  [Odoo blueprint {self.name}]")
        return res, status_code

    @entry
    def post(self, model: str, data=None, context=None) -> Response:
        params = {'params': {'data': data or {}}}
        if context:
            params.update({'context': context})
        res, status_code = self.odoo_post(f"{self.url}/api/{model}", params=params)
        if status_code == 200:
            return res['result'], 200
        if status_code == 500:
            raise InternalServerError(f"{res}  [Odoo blueprint {self.name}]")
        return res, status_code

    @entry
    def put(self, model: str, rec_id: int, data=None) -> Response:
        params = {'params': {'data': data or {}}}
        res, status_code = self.odoo_put(f'{self.url}/api/{model}/{rec_id}', params)
        if status_code == 500:
            raise InternalServerError(f"{res}  [Odoo blueprint {self.name}]")
        return res, status_code

    @entry
    def put_(self, model: str, filters: Filters = None, data=None) -> Response:
        """Bulk update."""
        params = {'params': {'data': data or {}}}
        if filters:
            params.update({'filter': filters})
        res, status_code = self.odoo_put(f'{self.url}/api/{model}', params)
        if status_code == 500:
            raise InternalServerError(f"{res}  [Odoo blueprint {self.name}]")
        return res, status_code

    @entry
    def delete(self, model: str, rec_id: int) -> Response:
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
            raise AccessDenied()

    def _destroy_session(self):
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
                f'{self.url}/web/session/destroy/',
                data=json.dumps(data),
                headers={'Content-type': 'application/json'}
            )

            return "", 200
        except Exception as e:
            return str(e), 401
