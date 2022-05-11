import base64
import json
import os
import typing as t
import xmlrpc.client
from dataclasses import dataclass

import requests
from aws_xray_sdk.core import xray_recorder
from werkzeug.exceptions import BadRequest
from werkzeug.exceptions import Forbidden
from werkzeug.exceptions import NotFound

from coworks import Blueprint
from coworks import entry


@dataclass
class OdooBinding:
    url: str
    dbname: str
    user: str
    passwd: str
    uid: str


class Odoo(Blueprint):
    """Odoo blueprint.
    This blueprint uses the API Rest application which must be installed on ODOO server.

    .. versionchanged:: 0.7.3
        ``env_var_prefix`` parameter may be a dict of bind values.
        GraphQL removed.
    """

    def __init__(self, name='odoo', *, env_url_var_name: str = '', env_dbname_var_name: str = '',
                 env_user_var_name: str = '', env_passwd_var_name: str = '',
                 env_var_prefix: t.Optional[t.Union[str, t.Dict[str, str]]] = None, **kwargs):
        """
        @param env_url_var_name: environment variable name for the odoo url.
        @param env_dbname_var_name: environment variable name for the odoo database.
        @param env_user_var_name: environment variable name for the odoo user.
        @param env_passwd_var_name: environment variable name for the odoo password.
        @param env_var_prefix: global environment variable prefix name.
        """
        super().__init__(name=name, **kwargs)
        self._bind: t.Optional[OdooBinding] = None
        self._binds: t.Dict[str, OdooBinding] = {}
        self.env_var_prefix = env_var_prefix
        if env_var_prefix is None:
            self._env_url_var_name = env_url_var_name
            self._env_dbname_var_name = env_dbname_var_name
            self._env_user_var_name = env_user_var_name
            self._env_passwd_var_name = env_passwd_var_name

    def init_app(self, app):
        if self.env_var_prefix:
            if type(self.env_var_prefix) is dict:
                self._binds = {bind: get_prefixed_config(prefix) for bind, prefix in self.env_var_prefix.items()}
            else:
                self._bind = get_prefixed_config(self.env_var_prefix)
        else:
            self._bind = get_config(self._env_url_var_name, self._env_url_var_name, self._env_user_var_name,
                                    self._env_passwd_var_name)

    @entry
    def kw(self, model: str, method: str = "search_read", id: int = None, fields: t.List[str] = None,
           order: str = None, domain: t.List[t.Tuple[str, str, t.Any]] = None, limit: int = None, page_size: int = None,
           page: int = 0, ensure_one: bool = False, bind: str = None):
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
        @param bind: bind configuration to be used.

        .. versionchanged:: 0.7.3
            Added the ``bind`` parameter.
       """
        if id and domain:
            raise BadRequest("Domain and Id parameters cannot be defined tin same time")
        if id:
            domain = [[('id', '=', id)]]
        else:
            domain = domain if domain else [[]]

        params = {}
        if order:
            params.update({'order': order})
        if fields:
            params.update({'fields': fields})
        if limit:
            params.update({'limit': limit})
        if page:
            page_size = page_size or limit
            params.update({'offset': page * page_size})

        res = self.odoo_execute_kw(bind, model, method, domain, params)

        if method == 'search_count':
            return res

        if len(res) == 0:
            raise NotFound()
        if ensure_one:
            if len(res) != 1:
                raise NotFound("More than one element found and ensure_one parameters was set")
            return res[0]

        return {"ids": [rec['id'] for rec in res], "values": res}

    @entry
    def create(self, model: str, data: t.List[dict] = None, bind: str = None) -> int:
        """Creates new records for the model.

        See also: https://www.odoo.com/documentation/14.0/developer/reference/addons/orm.html#odoo.models.Model.create
        @param model: python as a dot separated class name.
        @param data: fields, as a list of dictionaries, to initialize and the value to set on them.
        @param bind: bind configuration to be used.
        See also:
        https://www.odoo.com/documentation/14.0/developer/reference/addons/orm.html#odoo.models.Model.with_context
        """
        return self.odoo_execute_kw(bind, model, "create", data)

    @entry
    def write(self, model: str, id: int, data: dict = None, bind: str = None) -> list:
        """Updates one record with the provided values.
        See also: https://www.odoo.com/documentation/14.0/developer/reference/addons/orm.html#odoo.models.Model.write
        @param model: python as a dot separated class name.
        @param id: id of the record.
        @param data: fields to update and the value to set on them.
        @param bind: bind configuration to be used.
        """
        return self.odoo_execute_kw(bind, model, "write", [[id], data])

    @entry
    def delete_(self, model: str, id: int, bind: str = None) -> list:
        """delete the record.
        See also: https://www.odoo.com/documentation/14.0/developer/reference/addons/orm.html#odoo.models.Model.unlink
        @param model: python as a dot separated class name.
        @param id: id of the record.
        @param bind: bind configuration to be used.
        """
        return self.odoo_execute_kw(bind, model, "unlink", [[id]])

    @entry
    def get_pdf(self, report_id: int, rec_ids: t.List[str], bind: str = None) -> bytes:
        """Returns the PDF document attached to a report.
        Specif entry to allow PDF base64 encoding with JSON_RPC.

        @param report_id: id of the report record (ir.actions.report).
        @param rec_ids: records needed to generate the report.
        @param bind: bind configuration to be used.
        """

        if bind:
            config = self.get_bind(bind)
        else:
            config = self._bind
        try:
            headers = {'Content-type': 'application/json'}
            data = {'jsonrpc': "2.0", 'params': {'db': config.dbname, 'login': config.user, 'password': config.passwd}}
            res = requests.post(f'{config.url}/web/session/authenticate/', data=json.dumps(data), headers=headers)
            result = res.json()
            if result['result']['session_id']:
                session_id = res.cookies["session_id"]
                data = {'jsonrpc': "2.0", 'session_id': session_id}
                params = {'params': {'res_ids': json.dumps(rec_ids)}}
                try:
                    res = requests.post(f"{config.url}/report/{report_id}", params=data, json=params)
                    result = res.json()
                    if 'error' in result:
                        raise NotFound(f"{result['error']['message']}:{result['error']['data']}")
                    return base64.b64decode(result['result'])
                except NotFound:
                    raise
                except Exception:
                    raise BadRequest(res.text)
        except NotFound:
            raise
        except Exception:
            raise Forbidden()

    @xray_recorder.capture()
    def odoo_execute_kw(self, bind, model, method, *args, **kwargs):
        """Standard externalm API entries.
        See also: https://www.odoo.com/documentation/15.0/developer/misc/api/odoo.html
        """
        if bind:
            config = self.get_bind(bind)
        else:
            config = self._bind
        models = xmlrpc.client.ServerProxy(f'{config.url}/xmlrpc/2/object')
        return models.execute_kw(config.dbname, config.uid, config.passwd, model, method, *args, **kwargs)

    def get_bind(self, bind: str) -> OdooBinding:
        assert (bind in self._binds), f"Bind {bind} is not configured by 'env_var_prefix'."
        return self._binds[bind]


def get_prefixed_config(env_var_prefix: str):
    env_url_var_name = f"{env_var_prefix}_URL"
    env_dbname_var_name = f"{env_var_prefix}_DBNAME"
    env_user_var_name = f"{env_var_prefix}_USER"
    env_passwd_var_name = f"{env_var_prefix}_PASSWD"
    return get_config(env_url_var_name, env_dbname_var_name, env_user_var_name, env_passwd_var_name)


def get_config(env_url_var_name: str, env_dbname_var_name: str, env_user_var_name: str, env_passwd_var_name: str):
    url = os.getenv(env_url_var_name)
    if not url:
        raise EnvironmentError(f'{env_url_var_name} not defined in environment.')
    dbname = os.getenv(env_dbname_var_name)
    if not dbname:
        raise EnvironmentError(f'{env_dbname_var_name} not defined in environment.')
    user = os.getenv(env_user_var_name)
    if not user:
        raise EnvironmentError(f'{env_user_var_name} not defined in environment.')
    passwd = os.getenv(env_passwd_var_name)
    if not passwd:
        raise EnvironmentError(f'{env_passwd_var_name} not defined in environment.')

    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(dbname, user, passwd, {})

    return OdooBinding(url, dbname, user, passwd, uid)
