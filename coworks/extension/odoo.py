import base64
import os
import typing as t
import xmlrpc.client
from datetime import date
from datetime import datetime
from math import ceil

import requests
from aws_xray_sdk.core import xray_recorder
from coworks import TechMicroService
from coworks.extension.xray import XRay
from flask import json
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from werkzeug.exceptions import BadRequest
from werkzeug.exceptions import Forbidden
from werkzeug.exceptions import NotFound

from neorezo.models import CoercedStr
from .jsonapi import FetchingContext
from .jsonapi import JsonApiBaseModelMixin


class JsonAPiOdooBaseModel(JsonApiBaseModelMixin):
    @property
    def jsonapi_id(self) -> str:
        return str(self.id)

    def jsonapi_model_dump(self, context: FetchingContext):
        data = self.model_dump()
        fields = context.field_names(self.jsonapi_type)
        return {k: v for k, v in data.items() if not fields or k in fields}


class Report(BaseModel, JsonAPiOdooBaseModel):
    jsonapi_type: t.ClassVar[str] = "ir.actions.report"

    id: CoercedStr
    report_name: str


class Invoice(BaseModel, JsonAPiOdooBaseModel):
    jsonapi_type: t.ClassVar[str] = "account.invoice"

    id: CoercedStr
    create_date: datetime
    date_invoice: date
    type: str
    name: str
    state: str
    amount_untaxed_signed: float
    amount_tax: float
    amount_total_signed: float
    residual_signed: float

    first_name: str = Field(validation_alias='x_first_name')
    last_name: str = Field(validation_alias='x_last_name')
    company: str = Field(validation_alias='x_company')
    address_line1: str = Field(validation_alias='x_address_line1')
    address_line2: str = Field(validation_alias='x_address_line2')
    postal_code: str = Field(validation_alias='x_postal_code')
    city: str = Field(validation_alias='x_city')
    country: str | bool = Field(validation_alias='x_country')
    web_hidden: bool = Field(validation_alias='x_web_hidden')

    partner: "Partner" = None
    lines: t.List["InvoiceLine"]


class InvoiceLine(BaseModel, JsonAPiOdooBaseModel):
    jsonapi_type: t.ClassVar[str] = "account.invoice.line"

    id: CoercedStr


class Partner(BaseModel, JsonAPiOdooBaseModel):
    jsonapi_type: t.ClassVar[str] = "res.partner"

    id: CoercedStr


Invoice.model_rebuild()

odoo_models = {m.jsonapi_type: m for m in (Invoice, InvoiceLine, Partner, Report)}  # type: ignore[attr-defined]


class OdooConfig(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ref: t.Optional[str] = "default"
    url: str
    dbname: str
    user: str
    passwd: str
    const: t.Optional[dict[str, t.Any]] = Field(default_factory=dict)

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

        return OdooConfig(url=url, dbname=dbname, user=user, passwd=passwd)


class OdooPagination(BaseModel):
    page: int | None = 1
    per_page: int | None = 20
    max_per_page: int | None = 100
    total: int | None = None
    query: t.Any | None = None

    def model_post_init(self, __context: t.Any) -> None:
        if self.page is None:
            self.page = 1
        if self.per_page is None:
            self.per_page = 20
        if self.max_per_page is None:
            self.max_per_page = 100

    @property
    def pages(self) -> int:
        if not self.total:
            return 1
        return ceil(self.total / self.per_page)

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def prev_num(self) -> int | None:
        if not self.has_prev:
            return None
        return self.page - 1

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def next_num(self) -> int | None:
        if not self.has_next:
            return None
        return self.page + 1

    def __iter__(self):
        return iter(self.query.odoo_execute_kw(self.params))

    @property
    def params(self):
        return {
            'limit': self.per_page,
            'offset': (self.page - 1) * self.per_page,
        }


class OdooQuery(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    odoo: "Odoo"
    model: str
    method: str
    domain: list[tuple[str, str, t.Any]] | None
    bind: str | None = None  # config id in the binds list

    def paginate(self, *, page=None, per_page=None, max_per_page=None) -> OdooPagination:
        pagination = OdooPagination(page=page, per_page=per_page, max_per_page=max_per_page)
        pagination.query = self
        res = self.odoo.odoo_execute_kw(self.bind, self.model, "search_count", [self.domain])
        pagination.total = res
        return pagination

    def all(self, limit=2) -> list[JsonApiBaseModelMixin]:
        """Mainly used only to get one resource so set limit to 2."""
        params = {
            'limit': limit,
            'offset': 0,
        }
        return self.odoo_execute_kw(params)

    def odoo_execute_kw(self, params):
        res = self.odoo.odoo_execute_kw(self.bind, self.model, self.method, [self.domain], params)
        return [odoo_models[self.model](**rec) for rec in res]


class Odoo:
    """Flask's extension for Odoo.
    This extension uses the external API of ODOO.

    .. versionchanged:: 0.7.3
        ``env_var_prefix`` parameter may be a dict of bind values.
        GraphQL removed.
    """

    def __init__(self, app: TechMicroService | None = None,
                 config: OdooConfig | None = None, binds: dict[str | None, OdooConfig] = None):

        """
        :param app: Flask application.
        :param config: default configuration if no bind given in execution.
        :param binds: list of configuration binds.
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
    def query(self, model: str, method: str = "search_read", domain: list[tuple[str, str, t.Any]] | None = None,
              bind: str | None = None):
        return OdooQuery(odoo=self, model=model, method=method, domain=domain, bind=bind)

    @XRay.capture(xray_recorder)
    def kw(self, model: str, method: str = "search_read", id: int = None, fields: list[str] | None = None,
           order: str | None = None, domain: list[tuple[str, str, str]] | None = None, limit: int | None = None,
           page_size: int | None = None, page: int = 0, ensure_one: bool = False, bind: str | None = None):
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
