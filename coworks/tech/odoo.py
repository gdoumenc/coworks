import logging
import os
import io
import uuid
from http.client import BadStatusLine
from xmlrpc import client

import requests
from pyexpat import ExpatError
from datetime import datetime

from coworks.mixins import Boto3Mixin, AwsS3Session
from .. import Blueprint
from ..coworks import TechMicroService


class OdooMicroService(TechMicroService, Boto3Mixin):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.url = self.db = self.username = self.password = self.models_url = self.api_uid = self.logger = None
        # self.aws_s3_session = AwsS3Session()

        # @self.before_first_activation
        # def check_env_vars():
        #     self.bucket = os.getenv('BUCKET')
        #     if not self.bucket:
        #         raise EnvironmentError('BUCKET not defined in environment')

    def uplod_to_s3(self, file_obj, expiration=3600):
        """ Upload a file to s3 and return a presigned url to download it """
        try:
            response = self.aws_s3_session.client.upload_fileobj(file_obj, self.bucket, file_obj.name)
        except Exception as e:
            print(e)
        try:
            response = self.aws_s3_session.client.generate_presigned_url('get_object',
                                                                         Params={'Bucket': self.bucket,
                                                                                 'Key': file_obj.name},
                                                                         ExpiresIn=expiration)
            return response
        except Exception as e:
            print(e)

    def get_model(self, model: str, searched_field: str, searched_value=None, fields=None, searched_type="str",
                  ensure_one=False, **kwargs):
        """Returns the list of objects or the object which searched_field is equal to the searched_value."""
        if not searched_value:
            return BadRequestError(f"{searched_field} not defined.")

        convert = str
        if searched_type == "int":
            convert = int
        results = self.search(model, [[(searched_field, '=', convert(searched_value))]],
                              fields=fields if fields else [],
                              **kwargs)

        if ensure_one:
            return self._ensure_one(results)

        if not results:
            raise NotFoundError("No object found")
        return results

    def search_records_which_equals_to_json_data(self, model, data, fields):
        criteria = []
        for field_name, field_value in data.items():
            criterion = (field_name, '=', field_value)
            criteria.append(criterion)
        results = self.search(model, filters=[criteria], fields=fields)
        return results

    def put_model(self, model, data=None):
        return self.create(model, data)

    def put_model_(self, model, _id, data=None):
        """Replaces the object of the model referenced by this id."""
        return self.write(model, _id, data)

    def delete_model(self, model, _id, dry=False):
        """Deletes the object of the model referenced by this id."""
        return self.execute_kw(model, 'unlink', [[int(_id)]], dry=dry)

    def get_field(self, model, searched_field, searched_value, returned_field='id'):
        """Returns the value of the object which searched_field is equal to the searched_value."""
        value = self.get_model(model, searched_field, searched_value, fields=[returned_field], ensure_one=True)
        return value[returned_field]

    def get_id(self, model, searched_field, searched_value):
        """Returns the id of the object which searched_field is equal to the searched_value."""
        return self.get_field(model, searched_field, searched_value)

    def post_call(self, model: str, method: str, params_or_filters=None, options=None):
        params_or_filters = params_or_filters or [[]]
        options = options or {}
        return self.execute_kw(model, method, [params_or_filters], options)

    def execute_kw(self, model: str, method: str, *args, dry=False):
        try:
            if not model:
                raise ChaliceViewError("Model undefined")

            if not self.api_uid:
                self._connect()
            self.logger.info(f'Execute_kw : {model}, {method}, {list(args)}')
            if dry:
                return

            with client.ServerProxy(self.models_url, allow_none=True) as models:
                return models.execute_kw(self.db, self.api_uid, self.password, model, method, *args)
        except (BadStatusLine, ExpatError):
            self.logger.debug(f'Retry execute_kw : {model} {method} {args}')
            with client.ServerProxy(self.models_url) as models:
                return models.execute_kw(self.db, self.api_uid, self.password, model, method, *args)
        except Exception as e:
            raise

    def search(self, model, filters: list, fields=None, offset=None, limit=None, order=None) -> list:
        options = {}
        if fields:
            options["fields"] = fields if type(fields) is list else [fields]
        options.setdefault("offset", int(offset) if offset else 0)
        options.setdefault("limit", int(limit) if limit else 50)
        options.setdefault("order", order if order else 'id asc')
        return self.execute_kw(model, 'search_read', filters, options)

    def get_invoice(self, id):
        access_token = self.get_field('account.invoice', 'id', id, 'access_token')
        tenant = self.get_field('account.invoice', 'id', id, 'x_tenant')
        host = self.url
        url = f"{host}/my/invoices/{id}/?report_type=pdf&download=true&access_token={access_token}"
        res = requests.get(url=url)
        file_obj = io.BytesIO(res.content)
        file_obj.name = f"invoices/{str(tenant)}/invoice_{id}.pdf"
        if res.status_code == 200:
            return self.uplod_to_s3(file_obj)
        else:
            raise NotFoundError(f"Couldn't retreive invoice {id}, status_code : {res.status_code}")

    def post_test(self):
        return 'ok post'

    def post_testdata(self, data=None):
        return 'ok with data'

    def get_test(self):
        return 'ok get'

    def put_invoice(self, data=None):
        """ Put a new invoice in Odoo database
        Example json body :
        {
            "data": {
                "partner_id": 10,
                "lines": [
                    {
                        "product_id": "24",
                        "name": "description of the first product",
                        "quantity": 1,
                        "price_unit": 20,
                    },
                    {
                        "product_id": "24",
                        "name": "description of the second product",
                        "quantity": 2,
                        "price_unit": 21,
                    }
                ]
            }
        }
        """

        invoice_data = dict(data)
        if 'state' not in invoice_data:
            invoice_data['state'] = 'draft'
        if 'access_token' not in invoice_data:
            invoice_data['access_token'] = str(uuid.uuid4())
        if 'date_invoice' not in invoice_data:
            invoice_data['date_invoice'] = datetime.today().strftime('%Y-%m-%d')
        if 'x_order_id' not in invoice_data:
            raise BadRequestError("Order must have x_order_id field filled in")
        x_order_id = invoice_data['x_order_id']
        if 'x_tenant' not in invoice_data:
            raise BadRequestError("Order must have x_tenant field filled in")
        x_tenant = invoice_data['x_tenant']

        invoice_ids = self.search_records_which_equals_to_json_data('account.invoice', {'x_order_id': x_order_id, 'x_tenant': x_tenant}, 'id')

        if len(invoice_ids) != 0:
            raise BadRequestError(
                f"One or several invoices with x_order_id={x_order_id} and x_tenant={x_tenant} already exists, invoice_ids : {invoice_ids}")

        invoice_data.pop('lines')
        invoice_id = self.execute_kw('account.invoice', 'create', [[invoice_data]])[0]

        invoice_lines_data = data['lines']
        for invoice_line in invoice_lines_data:
            if not ('product_id' in invoice_line or 'product_name' in invoice_line):
                raise BadRequestError(
                    "All invoice lines must have their associated product_id or product_name filled in")

            if 'product_name' in invoice_line:
                product_id = self.get_field('product.product', 'product_tmpl_id.name', invoice_line['product_name'],
                                            returned_field='id')
                invoice_line['product_id'] = product_id

            if 'price_unit' not in invoice_line:
                raise BadRequestError(
                    "All invoice lines must have their associated price_unit (per-unit price) filled in")
            if 'account_id' not in invoice_line:
                # in this case use the default_credit_account_id associated to the journal 'Customer Invoices'
                account_id = \
                    self.get_field('account.journal', 'code', 'INV', returned_field='default_credit_account_id')[0]
                invoice_line['account_id'] = account_id

            try:
                taxes_id = self.get_field('product.product', 'id', invoice_line['product_id'],
                                          returned_field='taxes_id')
            except NotFoundError as e:
                raise BadRequestError(f"Invoicing product with id {invoice_line['product_id']} not found in Odoo")

            invoice_line['invoice_id'] = invoice_id
            invoice_line['invoice_line_tax_ids'] = [(6, 0, taxes_id)]  # 6,0 is odoo orm specific code
            # https://stackoverflow.com/questions/39892201/what-does-6-0-do-in-open-erp-7-code

        self.execute_kw('account.invoice.line', 'create', [invoice_lines_data])
        self.execute_kw('account.invoice', 'compute_taxes', [invoice_id])
        self.execute_kw('account.invoice', 'action_invoice_open', [invoice_id])
        return {'invoice_id': invoice_id}

    def post_createcustomer(self, data=None):
        """ Create a new customer (Odoo partner of type contact) in Odoo database
         Example json body :
         {
            "data": {
                    "name": "name",
                    "street": "street",
                    "city": "city",
                    "zip": "69007",
                    "email": "user@email.com",
                    "street2": "street2",
                    "phone": "04 00 00 00 00",
                    "mobile": "06 00 00 00 00"
                }
        }
        """
        data['type'] = 'contact'
        if 'name' not in data:
            raise BadRequestError(f"Customer must have a name specified in the json body")
        partner_id = self.execute_kw('res.partner', 'create', [[data]])
        return {'partner_id': partner_id[0]}

    def put_updatecustomer(self, id, data=None):
        """ Update info of a given customer (Odoo partner of type contact) in Odoo database
         Example json body :
         {
            "data": {
                    "name": "name",
                    "street": "street",
                    "city": "city",
                    "zip": "69007",
                    "email": "user@email.com",
                    "street2": "street2",
                    "phone": "04 00 00 00 00",
                    "mobile": "06 00 00 00 00"
                }
        }
        """
        data['type'] = 'contact'
        if 'name' not in data:
            raise BadRequestError(f"Customer must have a name specified in the json body")
        self.execute_kw('res.partner', 'write', [[id], data])
        return {'partner_id': id}

    def post_createinvoicingaddress(self, data=None):
        """ Create a new invoicing address (Odoo partner of type invoice) in Odoo database if an address
        with same fields content doesn't exist yet
                Example json body :
                {
                   "data": {
                           "name": "name",
                           "customer_id": "123",
                           "street": "street",
                           "city": "city",
                           "zip": "69007",
                           "email": "user@email.com",
                           "street2": "street2",
                           "phone": "04 00 00 00 00",
                           "mobile": "06 00 00 00 00"
                       }
               }
               """
        data['type'] = 'invoice'
        if 'name' not in data:
            raise BadRequestError(f"Invoicing address must have a name specified in the json body")
        if 'customer_id' not in data:
            raise BadRequestError(f"Invoicing address must have its associated customer_id specified in the json body")
        data['commercial_partner_id'] = data['customer_id']
        data['parent_id'] = data['customer_id']
        data.pop('customer_id')

        partner_ids = self.search_records_which_equals_to_json_data('res.partner', data, 'id')

        if len(partner_ids) == 0:  # create new address
            partner_id = self.execute_kw('res.partner', 'create', [[data]])
            return {'partner_id': partner_id[0]}
        elif len(partner_ids) == 1:  # one address with same fields content already exists
            return {'partner_id': partner_ids[0]['id']}
        else:
            return BadRequestError('Several addresses exist with these data')

    def create(self, model, data: dict, dry=False):
        return self.execute_kw(model, 'create', [self._replace_tuple(data)], dry=dry)

    def write(self, model, _id, data: dict, dry=False):
        return self.execute_kw(model, 'write', [[_id], self._replace_tuple(data)], dry=dry)

    def _connect(self, url=None, database=None, username=None, password=None):

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

    @staticmethod
    def _ensure_one(results) -> dict:
        """Ensure only only one in the result list and returns it."""
        if len(results) == 0:
            raise NotFoundError(f"No object found.")
        if len(results) > 1:
            raise NotFoundError(
                f"More than one object ({len(results)}) founds : ids={[o.get('id') for o in results]}")
        return results[0]

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


class OdooBlueprint(Blueprint):
    def __init__(self, model, common_filters=None, **kwargs):
        super().__init__(**kwargs)
        self._model = model
        self._common_filters = common_filters if common_filters else []

    def search(self, filters: list, fields=None, offset=None, limit=None, order=None, **options):
        filters = [self._common_filters + f for f in filters]
        return self.current_app.search(self._model, filters, fields, offset, limit, order, **options)

    def create(self, data, dry=False):
        return self.current_app.put_model(self._model, data, dry=dry)

    def write(self, _id, data, dry=False):
        return self.current_app.put_model(self._model, _id, data, dry=dry)

    def delete(self, _id, dry=False):
        return self.current_app.delete_model(self._model, _id, dry=dry)


class UserBlueprint(OdooBlueprint):

    def __init__(self, import_name='user', **kwargs):
        super().__init__("res.users", import_name=import_name, **kwargs)


class PartnerBlueprint(OdooBlueprint):

    def __init__(self, import_name='partner', **kwargs):
        super().__init__("res.partner", import_name=import_name, **kwargs)


class CustomerBlueprint(PartnerBlueprint):

    def __init__(self, import_name='customer', **kwargs):
        super().__init__(common_filters=[('customer', '=', True)], import_name=import_name, **kwargs)


class SupplierBlueprint(PartnerBlueprint):

    def __init__(self, import_name='supplier', **kwargs):
        super().__init__(common_filters=[('supplier', '=', True)], import_name=import_name, **kwargs)


class ProductBlueprint(OdooBlueprint):

    def __init__(self, import_name='product', **kwargs):
        super().__init__("product.product", import_name=import_name, **kwargs)
