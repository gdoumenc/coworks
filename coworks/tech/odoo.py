import logging
import os
from http.client import BadStatusLine
from pyexpat import ExpatError
from xmlrpc import client

from .. import Blueprint
from ..coworks import TechMicroService, ChaliceViewError


class OdooMicroService(TechMicroService):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.url = self.db = self.username = self.password = self.models_url = self.api_uid = self.logger = None

    def connect(self, url=None, database=None, username=None, password=None):

        # initialize connection informations
        self.url = url or os.getenv('ODOO_URL')
        if not self.url:
            raise EnvironmentError('ODOO_URL must be set before anything else!')
        self.db = database or os.getenv('ODOO_DB')
        if not self.db:
            raise EnvironmentError('ODOO_DB must be set before anything else!')
        self.username = username or os.getenv('ODOO_USERNAME')
        if not self.username:
            raise EnvironmentError('ODOO_USERNAME must be set before anything else!')
        self.password = password or os.getenv('ODOO_PASSWORD')
        if not self.password:
            raise EnvironmentError('ODOO_PASSWORD must be set before anything else!')

        self.logger = logging.getLogger('odoo')

        try:
            # initialize xml connection to odoo
            common = client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            self.api_uid = common.authenticate(self.db, self.username, self.password, {})
            if not self.api_uid:
                raise Exception(f'Odoo connection parameters are wrong')
            self.models_url = f'{self.url}/xmlrpc/2/object'
        except Exception:
            raise Exception(f'Odoo interface variables wrongly defined.')

    def execute_kw(self, model: str, method: str, *args):
        try:
            if not model:
                raise ChaliceViewError("Model undefined")

            if not self.api_uid:
                self.connect()
            self.logger.info(f'Execute_kw : {model}, {method}, {list(args)}')
            with client.ServerProxy(self.models_url) as models:
                return models.execute_kw(self.db, self.api_uid, self.password, model, method, *args)
        except (BadStatusLine, ExpatError):
            self.logger.debug(f'Retry execute_kw : {model} {method} {args}')
            with client.ServerProxy(self.models_url) as models:
                return models.execute_kw(self.db, self.api_uid, self.password, model, method, *args)
        except Exception as e:
            raise ChaliceViewError(str(e))


class OdooBlueprint(Blueprint):
    def __init__(self, name):
        super().__init__(name)
        self._model = None
        self._common_filters = []

    def get_id(self, id, fields=[]):
        return self.search([('id', '=', id)], fields=fields)

    def search(self, filters: list, fields=None, offset=None, limit=None, order=None, **options):
        if fields:
            options["fields"] = fields if type(fields) is list else [fields]
        options.setdefault("limit", offset if offset else 0)
        options.setdefault("limit", limit if limit else 50)
        options.setdefault("order", order if order else 'id asc')  # sep ,
        return self._current_app.execute_kw(self._model, 'search_read', [self._common_filters + filters], options)

    def create(self, data):
        return self._current_app.execute_kw(self._model, 'create', [self._common_filters + filters], options)

    def write(self, id, fields):
        return self._current_app.execute_kw(self._model, 'write', [[id], fields])


class PartnerBlueprint(OdooBlueprint):

    def __init__(self, name='partner'):
        super().__init__(name)
        self._model = "res.partner"

    def get_name(self, name, fields=None):
        return self.search([('name', '=', name)], fields=fields)

    def get_ref(self, ref):
        return self.search([('ref', '=', ref)])


class CustomerBlueprint(PartnerBlueprint):

    def __init__(self):
        super().__init__('customer')
        self._common_filters = [('customer', '=', True)]


class SupplierBlueprint(PartnerBlueprint):

    def __init__(self):
        super().__init__('supplier')
        self._common_filters = [('supplier', '=', True)]
