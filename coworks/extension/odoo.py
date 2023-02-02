import base64
import json
import os
import typing as t
import xmlrpc.client
from dataclasses import dataclass
from dataclasses import field

import requests
from aws_xray_sdk.core import xray_recorder
from werkzeug.exceptions import BadRequest
from werkzeug.exceptions import Forbidden
from werkzeug.exceptions import NotFound

from coworks.extension.xray import XRay


@dataclass
class OdooConfig:
    url: str
    dbname: str
    user: str
    passwd: str
    const: t.Dict[str, t.Any] = field(default_factory=dict)

    @classmethod
    def from_env_var_prefix(cls, env_var_prefix):
        env_url_var_name = f"{env_var_prefix}_URL"
        env_dbname_var_name = f"{env_var_prefix}_DBNAME"
        env_user_var_name = f"{env_var_prefix}_USER"
        env_passwd_var_name = f"{env_var_prefix}_PASSWD"
        return cls.get_config(env_url_var_name, env_dbname_var_name, env_user_var_name, env_passwd_var_name)

    @classmethod
    def get_config(cls, env_url_var_name: str, env_dbname_var_name: str, env_user_var_name: str,
                   env_passwd_var_name: str):
        url = os.getenv(env_url_var_name)
        if not url:
            raise RuntimeError(f'{env_url_var_name} not defined in environment.')
        dbname = os.getenv(env_dbname_var_name)
        if not dbname:
            raise RuntimeError(f'{env_dbname_var_name} not defined in environment.')
        user = os.getenv(env_user_var_name)
        if not user:
            raise RuntimeError(f'{env_user_var_name} not defined in environment.')
        passwd = os.getenv(env_passwd_var_name)
        if not passwd:
            raise RuntimeError(f'{env_passwd_var_name} not defined in environment.')

        return OdooConfig(url, dbname, user, passwd)


class Odoo:
    """Odoo extension.
    This extension uses the external API of ODOO.

    .. versionchanged:: 0.7.3
        ``env_var_prefix`` parameter may be a dict of bind values.
        GraphQL removed.
    """

    def __init__(self, app=None, config: OdooConfig = None, binds: t.Dict[t.Optional[str], OdooConfig] = None):
        """
        :param app: Flask application.
        :param config: default configuration.
        :param binds: configuration binds.
        """
        self.app = None

        self.binds = binds if binds else {}
        if config:
            self.binds[None] = config

        if app:
            self.init_app(app)

    def init_app(self, app):
        self.app = app

    @XRay.capture(xray_recorder)
    def kw(self, model: str, method: str = "search_read", id: int = None, fields: t.Iterator[str] = None,
           order: str = None, domain: t.Iterator[t.Tuple[str, str, t.Any]] = None, limit: int = None, page_size: int = None,
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
            domain = [domain] if domain else [[]]

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
            raise NotFound("No element found.")
        if ensure_one:
            if len(res) != 1:
                raise NotFound("More than one element found and ensure_one parameters was set")
            return res[0]

        return {"ids": [rec['id'] for rec in res], "values": res}

    @XRay.capture(xray_recorder)
    def create(self, model: str, data: t.Iterator[dict] = None, bind: str = None) -> int:
        """Creates new records for the model.

        See also: https://www.odoo.com/documentation/14.0/developer/reference/addons/orm.html#odoo.models.Model.create
        @param model: python as a dot separated class name.
        @param data: fields, as a list of dictionaries, to initialize and the value to set on them.
        @param bind: bind configuration to be used.
        See also:
        https://www.odoo.com/documentation/14.0/developer/reference/addons/orm.html#odoo.models.Model.with_context
        """
        return self.odoo_execute_kw(bind, model, "create", data)

    @XRay.capture(xray_recorder)
    def write(self, model: str, id: int, data: dict = None, bind: str = None) -> list:
        """Updates one record with the provided values.
        See also: https://www.odoo.com/documentation/14.0/developer/reference/addons/orm.html#odoo.models.Model.write
        @param model: python as a dot separated class name.
        @param id: id of the record.
        @param data: fields to update and the value to set on them.
        @param bind: bind configuration to be used.
        """
        return self.odoo_execute_kw(bind, model, "write", [[id], data])

    @XRay.capture(xray_recorder)
    def delete_(self, model: str, id: int, bind: str = None) -> list:
        """delete the record.
        See also: https://www.odoo.com/documentation/14.0/developer/reference/addons/orm.html#odoo.models.Model.unlink
        @param model: python as a dot separated class name.
        @param id: id of the record.
        @param bind: bind configuration to be used.
        """
        return self.odoo_execute_kw(bind, model, "unlink", [[id]])

    def get_pdf(self, report_id: int, rec_ids: t.Iterator[str], bind: str = None) -> bytes:
        """Returns the PDF document attached to a report.
        Specif entry to allow PDF base64 encoding with JSON_RPC.

        @param report_id: id of the report record (ir.actions.report).
        @param rec_ids: records needed to generate the report.
        @param bind: bind configuration to be used.
        """

        config = self.binds[bind]
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

    def odoo_execute_kw(self, bind, model, method, *args, **kwargs):
        """Standard externalm API entries.
        See also: https://www.odoo.com/documentation/15.0/developer/misc/api/odoo.html
        """
        config = self.binds[bind]

        if '__uid' not in config.const:
            common = xmlrpc.client.ServerProxy(f'{config.url}/xmlrpc/2/common')
            config.const['__uid'] = common.authenticate(config.dbname, config.user, config.passwd, {})

        models = xmlrpc.client.ServerProxy(f'{config.url}/xmlrpc/2/object')
        return models.execute_kw(config.dbname, config.const['__uid'], config.passwd, model, method, *args, **kwargs)
