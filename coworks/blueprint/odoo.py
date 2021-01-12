import os
import time
from http.client import BadStatusLine
from pyexpat import ExpatError
from typing import List, Tuple, Union, Optional
from xmlrpc import client
from xmlrpc.client import Fault, ProtocolError

from aws_xray_sdk.core import xray_recorder

from coworks.mixins import Boto3Mixin
from .. import Blueprint


class Odoo(Blueprint, Boto3Mixin):
    """Odoo blueprint."""

    def __init__(self, url_env_var_name='URL', dbname_env_var_name='DBNAME', user_env_var_name='USER',
                 passwd_env_var_name='PASSWD', **kwargs):
        super().__init__(**kwargs)
        self.url = self.dbname = self.user = self.passwd = None
        self.url_env_var_name = url_env_var_name
        self.dbname_env_var_name = dbname_env_var_name
        self.user_env_var_name = user_env_var_name
        self.passwd_env_var_name = passwd_env_var_name
        self.api_uid = None

    def get(self):
        """Check the connection."""
        try:
            self.connect()
            return "connected"
        except Exception as e:
            return str(e), 404

    def get_model(self, model: str, searched_field_or_domain: Union[str, List[Tuple[str, str, any]]],
                  searched_value = None, fields: Optional[List[str]] = None, ensure_one=False, **kwargs):
        """Returns the list of objects or the object which searched_field is equal to the searched_value."""
        if type(searched_field_or_domain) is list:
            filters = [searched_field_or_domain]
        else:
            filters = [[(searched_field_or_domain, '=', searched_value)]] if searched_field_or_domain else [[]]
        fields = fields or ['id']
        results = self.search(model, filters, fields=fields, ensure_one=ensure_one, **kwargs)
        return results

    def get_fields(self, model, searched_field, searched_value, fields=None):
        """Returns the value of the object which searched_field is equal to the searched_value."""
        fields = fields or ['id']
        return self.get_model(model, searched_field, searched_value, fields=fields, ensure_one=True)

    def get_field(self, model, searched_field, searched_value, fields='id'):
        """Returns the value of the object which searched_field is equal to the searched_value."""
        return self.get_model(model, searched_field, searched_value, fields=[fields], ensure_one=True)[0]

    def get_id(self, model, searched_field, searched_value):
        """Returns the id of the object which searched_field is equal to the searched_value."""
        return self.get_field(model, searched_field, searched_value)

    @xray_recorder.capture("Connect to ODOO")
    def connect(self, url=None, dbname=None, user=None, passwd=None):
        # initialize connection informations
        self.url = url or os.getenv(self.url_env_var_name)
        if not self.url:
            raise EnvironmentError(f"{self.url_env_var_name} not defined in environment.")
        self.dbname = dbname or os.getenv(self.dbname_env_var_name)
        if not self.dbname:
            raise EnvironmentError(f"{self.dbname_env_var_name} not defined in environment.")
        self.user = user or os.getenv(self.user_env_var_name)
        if not self.user:
            raise EnvironmentError(f"{self.user_env_var_name} not defined in environment.")
        self.passwd = passwd or os.getenv(self.passwd_env_var_name)
        if not self.passwd:
            raise EnvironmentError(f"{self.passwd_env_var_name} not defined in environment.")

        try:
            subsegment = xray_recorder.current_subsegment()
            if subsegment:
                subsegment.put_metadata("connection",
                                        f"Connection parameters: {self.url}, {self.dbname}, {self.user}, {self.passwd}")

            # initialize xml connection to odoo
            common = client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            self.api_uid = common.authenticate(self.dbname, self.user, self.passwd, {})
            if not self.api_uid:
                raise Exception(f'Odoo connection parameters are wrong.')
        except Exception:
            raise Exception(f'Odoo interface variables wrongly defined.')

    @xray_recorder.capture()
    def execute_kw(self, model: str, method: str, *args):
        if not self.api_uid:
            self.connect()
        models_url = f'{self.url}/xmlrpc/2/object'
        try:
            with client.ServerProxy(models_url, allow_none=True) as models:
                res: List[dict] = models.execute_kw(self.dbname, self.api_uid, self.passwd, model, method, *args)
                return res
        except (BadStatusLine, ExpatError, ProtocolError):
            time.sleep(2)
            with client.ServerProxy(models_url) as models:
                return models.execute_kw(self.dbname, self.api_uid, self.passwd, model, method, *args)
        except Fault as e:
            if e.faultString.endswith("TypeError: cannot marshal None unless allow_none is enabled\n"):
                return
            raise
        except Exception as e:
            raise

    def search(self, model, filters: List[List[tuple]], *, fields=None, offset=None, limit=None, order=None,
               ensure_one: bool = False) -> Union[Tuple[str, int], dict, List[dict]]:
        options = {}
        if fields:
            options["fields"] = fields if type(fields) is list else [fields]
        options.setdefault("offset", int(offset) if offset else 0)
        options.setdefault("limit", int(limit) if limit else 50)
        options.setdefault("order", order if order else 'id asc')

        try:
            results = self.execute_kw(model, 'search_read', filters, options)
            return _reduce_result(results, fields, ensure_one)
        except Exception as e:
            return str(e), 404

    def create(self, model, data: dict):
        return self.execute_kw(model, 'create', [self._replace_tuple(data)])

    def write(self, model, _id, data: dict):
        return self.execute_kw(model, 'write', [[_id], self._replace_tuple(data)])

    # def delete(self, model, _id):
    #     return self.execute_kw(model, 'unlink', [[_id]])

    def _replace_tuple(self, struct: dict) -> dict:
        """For data from JSON, tuple are defined with key surronded by paranthesis."""
        for k, value in struct.items():
            if isinstance(value, dict):
                self._replace_tuple(value)
            else:
                if k.startswith('(') and type(value) is list:
                    del struct[k]
                    struct[k[1:-1]] = [tuple(v) for v in value]
        return struct


def _reduce_result(results: List[dict], fields, ensure_one):
    """Reduces rows values if only one value and ensure only only one in the result list and returns it."""
    if len(fields) == 1:
        results = [row[fields[0]] for row in results]
    if ensure_one:
        if len(results) == 0:
            return "No object found.", 404
        if len(results) > 1:
            return f"More than one object ({len(results)}) founds : ids={[o.get('id') for o in results]}", 404
        return results[0]
    return results
