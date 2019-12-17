import logging
import os
from http.client import BadStatusLine
from pyexpat import ExpatError
from xmlrpc import client

from ..coworks import TechMicroService


class OdooMicroService(TechMicroService):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = self.db = self.username = self.password = self.models_url = self.api_uid = self.logger = None

    def connect(self, url=None, database=None, username=None, password=None, ):

        # initialize connection informations
        self.url = url or os.getenv('ODOO_URL', False)
        if not self.url:
            raise EnvironmentError('ODOO_URL must be set before anything else!')
        self.db = database or os.getenv('ODOO_DB', False)
        if not self.db:
            raise EnvironmentError('ODOO_DB must be set before anything else!')
        self.username = username or os.getenv('ODOO_USERNAME', False)
        if not self.username:
            raise EnvironmentError('ODOO_USERNAME must be set before anything else!')
        self.password = password or os.getenv('ODOO_PASSWORD', False)
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
            raise e
