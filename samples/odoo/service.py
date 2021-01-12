import datetime
from dataclasses import dataclass

from aws_xray_sdk.core import xray_recorder
from jinja2 import Environment, FileSystemLoader, select_autoescape

from coworks import TechMicroService, jsonify
from coworks.blueprint import Admin
from coworks.blueprint.odoo import Odoo
from coworks.config import Config as CwsConfig
from coworks.context_manager import XRayContextManager


@dataclass
class Config(CwsConfig):
    environment_variables_file: str = "vars.json"


class SimpleOdooMicroService(TechMicroService):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_blueprint(Odoo())
        self.jinja_env = Environment(
            loader=FileSystemLoader("templates"),
            autoescape=select_autoescape(['html', 'xml'], default_for_string=True)
        )

    @property
    def invoices(self):
        domain = [("date_invoice", '=', datetime.date.today().strftime("%Y-%m-%d"))]
        return self.entry('/model/{0}/{1}').call_get('account.invoice', domain,
                                                     fields=['id', 'name', 'amount_untaxed'],
                                                     limit=5000)
        # invoices = self.entry_get('/model', 'account.invoice', "id", 3329, fields=['id', 'name'], limit=5000)

    def get_invoices(self):
        return jsonify(self.invoices)

    def get_table(self):
        template_filename = 'table.j2'
        template = self.jinja_env.get_template(template_filename)
        headers = {'Content-Type': 'text/html; charset=utf-8'}
        return template.render({'invoices': self.invoices}), 200, headers

    def get_dashboard(self):
        template_filename = 'dashboard.j2'
        template = self.jinja_env.get_template(template_filename)
        headers = {'Content-Type': 'text/html; charset=utf-8'}
        return template.render(), 200, headers


odoo = SimpleOdooMicroService(configs=[Config()])
odoo.register_blueprint(Admin(), url_prefix='admin')
XRayContextManager(odoo, xray_recorder)

if __name__ == '__main__':
    from coworks.cws.runner import run_with_reloader

    run_with_reloader(odoo, project_dir='.', module='service', workspace='dev')
