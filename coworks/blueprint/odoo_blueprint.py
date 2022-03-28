import base64
import json
import os
import typing as t
import xmlrpc.client

import requests
from aws_xray_sdk.core import xray_recorder
from flask import Response
from werkzeug.exceptions import BadRequest
from werkzeug.exceptions import Forbidden
from werkzeug.exceptions import NotFound

from coworks import Blueprint
from coworks import entry


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

        @self.before_app_request
        def set_session():
            if not self.uid:
                raise Forbidden()

    def init_app(self, app):
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

    @entry
    def kw(self, model: str, method: str = "search_read", id: int = None, fields: t.List[str] = None,
           order: str = None, domain: t.List[t.Tuple[str, str, t.Any]] = None, limit: int = None, page_size: int = None,
           page: int = 0, ensure_one: bool = False):
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
            raise BadRequest("Domain and Id parameters cannot be defined tin same time")

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

        res = self.odoo_execute_kw(model, method, domain, params)

        if method == 'search_count':
            return res

        if len(res) == 0:
            raise NotFound()
        if ensure_one:
            if len(res) > 1:
                raise NotFound("More than one element found and ensure_one parameters was set")
            return res[0]

        return {"ids": [rec['id'] for rec in res], "values": res}

    @entry
    def gql(self, query: str = None):
        """Searches with GraphQL query for records based on the query.
        @param query: graphQL query.
        """
        if not query:
            raise BadRequest()
        return self.odoo_execute_gql({'query': query})

    @entry
    def create(self, model: str, data: t.List[dict] = None):
        """Creates new records for the model.
        See also: https://www.odoo.com/documentation/14.0/developer/reference/addons/orm.html#odoo.models.Model.create
        @param model: python as a dot separated class name.
        @param data: fields, as a list of dictionaries, to initialize and the value to set on them.
        See also:
        https://www.odoo.com/documentation/14.0/developer/reference/addons/orm.html#odoo.models.Model.with_context
        """
        return self.odoo_execute_kw(model, "create", data)

    @entry
    def write(self, model: str, id: int, data: dict = None) -> Response:
        """Updates one record with the provided values.
        See also: https://www.odoo.com/documentation/14.0/developer/reference/addons/orm.html#odoo.models.Model.write
        @param model: python as a dot separated class name.
        @param id: id of the record.
        @param data: fields to update and the value to set on them.
        """
        return self.odoo_execute_kw(model, "write", [[id], data])

    @entry
    def delete_(self, model: str, id: int) -> Response:
        """delete the record.
        See also: https://www.odoo.com/documentation/14.0/developer/reference/addons/orm.html#odoo.models.Model.unlink
        @param model: python as a dot separated class name.
        @param id: id of the record.
        """
        return self.odoo_execute_kw(model, "unlink", [[id]])

    @entry
    def get_pdf(self, report_id: int, rec_ids: t.List[str]) -> bytes:
        """Returns the PDF document attached to a report.
        Specif entry to allow PDF base64 encoding with JSON_RPC.

        @param report_id: id of the record.
        @param rec_ids: records needed to generate the report.
        """

        try:
            headers = {'Content-type': 'application/json'}
            data = {'jsonrpc': "2.0", 'params': {'db': self.dbname, 'login': self.user, 'password': self.passwd}}
            res = requests.post(f'{self.url}/web/session/authenticate/', data=json.dumps(data), headers=headers)
            result = res.json()
            if result['result']['session_id']:
                session_id = res.cookies["session_id"]
                data = {'jsonrpc': "2.0", 'session_id': session_id}
                params = {'params': {'res_ids': json.dumps(rec_ids)}}
                try:
                    res = requests.post(f"{self.url}/report/{report_id}", params=data, json=params)
                    result = res.json()
                    if 'error' in result:
                        raise NotFound(f"{result['error']['message']}:{result['error']['data']}")
                    return base64.b64decode(result['result'])
                except Exception as e:
                    raise BadRequest(res.text)
        except Exception as e:
            raise AccessDenied()

    @xray_recorder.capture()
    def odoo_execute_kw(self, model, method, *args, **kwargs):
        """Standard externalm API entries.
        See also: https://www.odoo.com/documentation/15.0/developer/misc/api/odoo.html
        """
        models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
        return models.execute_kw(self.dbname, self.uid, self.passwd, model, method, *args, **kwargs)

    @xray_recorder.capture()
    def odoo_execute_gql(self, query, **kwargs):
        """GraphQL's entry.
        See also: https://apps.odoo.com/apps/modules/12.0/graphql_base/
        """
        headers = {"Authorization": self.passwd, "Content-Type": "application/json"}
        res = requests.post(f'{self.url}/graphql', json=query, headers=headers)
        return res.json()
