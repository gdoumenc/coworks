import datetime
from aws_xray_sdk.core import xray_recorder
from jinja2 import Environment, FileSystemLoader, select_autoescape
from typing import cast

from coworks import TechMicroService, entry
from coworks.blueprint import Admin
from coworks.blueprint.odoo_blueprint import Odoo
from coworks.context_manager import XRayContextManager


class SimpleOdooMicroService(TechMicroService):

    def __init__(self, env_var_prefix, **kwargs):
        super().__init__(**kwargs)
        self.register_blueprint(Admin(), url_prefix='admin')
        self.register_blueprint(Odoo(env_var_prefix=env_var_prefix))
        self.jinja_env = Environment(
            loader=FileSystemLoader("templates"),
            autoescape=select_autoescape(['html', 'xml'], default_for_string=True)
        )

    @property
    def odoo(self):
        return cast(Odoo, self.blueprints['odoo'])

    @entry
    def get_invoice(self):
        """Get today invoices."""
        filters = [("date_invoice", '=', datetime.date.today().strftime("%Y-%m-%d"))]
        query = "{id,name,amount_untaxed}"
        data, status_code = self.odoo.get('account.invoice', filters=filters, query=query)
        return data

    def get_table(self):
        template_filename = 'table.j2'
        template = self.jinja_env.get_template(template_filename)
        headers = {'Content-Type': 'text/html; charset=utf-8'}
        return template.render({'invoices': self.get_invoice()}), 200, headers

    def get_dashboard(self):
        template_filename = 'dashboard.j2'
        template = self.jinja_env.get_template(template_filename)
        headers = {'Content-Type': 'text/html; charset=utf-8'}
        return template.render(), 200, headers


odoo = SimpleOdooMicroService("ADZ_BILLING_ODOO")
XRayContextManager(odoo, xray_recorder)

if __name__ == '__main__':
    odoo.execute("run", project_dir='.', module='service', workspace='local')
