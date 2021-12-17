import json
import os
import typing as t
import xmlrpc.client

import requests
from aws_xray_sdk.core import xray_recorder
from coworks import Blueprint
from coworks import entry
from flask import Response
from flask import abort


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
        self.uid = None
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
        def check_env_vars():
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

            common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            self.uid = common.authenticate(self.dbname, self.user, self.passwd, {})

        @self.before_app_request
        def set_session():
            if not self.uid:
                abort(403)

            # TO BE REMOVED
            self.session_id, status_code = self.get_session_id_old()

    @entry
    def kw(self, model: str, method: str = "search_read", id: t.Union[int, str] = None, fields: t.List[str] = None,
           order: str = None, domain: t.List[t.Tuple[str, str, t.Any]] = None, limit: int = None, page_size=None,
           page=0, ensure_one=False):
        """Searches with API for records based on the args.
        See also: https://www.odoo.com/documentation/14.0/developer/reference/addons/orm.html#odoo.models.Model.search
        @param model: python as a dot separated class name.
        @param method : API method name maybe search_read, search_count
        @param id : id for one element
        @param fields: record fields for result.
        @param order: oder of result.
        @param domain: domain for records.
        @param limit: maximum number of records to return from odoo (default: all).
        @param page_size: pagination done by the microservice.
        @param page: current page searched.
        @param ensure_one: raise error if result is not one (404) and only one (400) object.
        """
        if id and domain:
            abort(Response("Domain and Id parameters cannot be defined tin same time", status=400))

        params = {}
        if id:
            domain = [[('id', '=', id)]]
        else:
            domain = domain if domain else [[]]
            if limit:
                params.update({'limit': limit})
            if order:
                params.update({'order': order})
            if page:
                page_size = page_size or limit
                params.update({'offset': page * page_size})
        if fields:
            params.update({'fields': fields})
        res, status_code = self.odoo_execute_kw(model, method, domain, params)
        if status_code != 200:
            abort(Response(res.text, status=status_code))

        if method == 'search_count':
            return res

        if len(res) == 0:
            return abort(Response("Not found", status=404))
        if ensure_one:
            if len(res) > 1:
                return abort(Response("More than one element found and ensure_one parameters was set", 404))
            return res[0]
        return {"ids": [rec['id'] for rec in res], "values": res}

    @entry
    def gql(self, query: str = None):
        """Searches with GraphQL query for records based on the query.
        @param query: graphQL query.
        """
        if not query:
            abort(400)
        res, status_code = self.odoo_execute_gql({'query': query})
        if status_code != 200:
            abort(status_code)
        return res

    @entry
    def create(self, model: str, data: t.List[dict] = None):
        """Creates new records for the model..
        See also: https://www.odoo.com/documentation/14.0/developer/reference/addons/orm.html#odoo.models.Model.create
        @param model: python as a dot separated class name.
        @param data: fields, as a list of dictionaries, to initialize and the value to set on them.
        See also: https://www.odoo.com/documentation/14.0/developer/reference/addons/orm.html#odoo.models.Model.with_context
        """
        return self.odoo_execute_kw(model, "create", data)

    @entry
    def write(self, model: str, id: t.Union[int, str], data: dict = None) -> Response:
        """Updates one record with the provided values.
        See also: https://www.odoo.com/documentation/14.0/developer/reference/addons/orm.html#odoo.models.Model.write
        @param model: python as a dot separated class name.
        @param id: id of the record.
        @param data: fields to update and the value to set on them.
        """
        return self.odoo_execute_kw(model, "write", [[id], data])

    @entry
    def delete_(self, model: str, rec_id: int) -> Response:
        """delete the record.
        See also: https://www.odoo.com/documentation/14.0/developer/reference/addons/orm.html#odoo.models.Model.unlink
        @param model: python as a dot separated class name.
        @param rec_id: id of the record.
        """
        res, status_code = self.odoo_delete(f'{self.url}/api/{model}/{rec_id}')
        if status_code == 200:
            return res['result']
        abort(status_code)

    @entry
    def get_pdf(self, report_id: int, rec_ids: t.List[str]):
        """Returns the PDF document attached to a report.
        @param report_id: id of the record.
        @param rec_ids: records needed to generate the report.
        """
        params = {'params': {'res_ids': json.dumps(rec_ids)}}
        res, status_code = self.odoo_post_old(f"{self.url}/report/{report_id}", params=params)
        if status_code != 200:
            abort(make_response(res, status_code))
        return res['result']

    @xray_recorder.capture()
    def odoo_execute_kw(self, model, method, *args, **kwargs):
        """Standard externalm API entries.
        See also: https://www.odoo.com/documentation/15.0/developer/misc/api/odoo.html
        """
        models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
        res = models.execute_kw(self.dbname, self.uid, self.passwd, model, method, *args, **kwargs)
        return res, 200

    @xray_recorder.capture()
    def odoo_execute_gql(self, query, **kwargs):
        """GraphQL entry defined.
        See also: https://apps.odoo.com/apps/modules/12.0/graphql_base/
        """
        headers = {"Authorization": self.passwd, "Content-Type": "application/json"}
        res = requests.post(f'{self.url}/graphql', json=query, headers=headers)
        return res.json(), 200

    def _get_uid(self):
        """Open or checks the connection."""
        try:
            common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            uid = common.authenticate(self.dbname, self.user, self.passwd, {})
            return uid, 200
        except Exception as e:
            return str(e), 401

    # TO BE REMOVED
    def odoo_post_old(self, path, params, headers=None) -> t.Tuple[t.Union[str, dict], int]:
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

    # TO BE REMOVED
    def get_session_id_old(self):
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
