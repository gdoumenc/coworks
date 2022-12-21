import os

import requests
from flask import send_from_directory
from flask_login import LoginManager

from account import AccountBlueprint
from coworks import TechMicroService
from coworks import __version__ as coworks_version
from coworks import entry
from coworks.blueprint.admin_blueprint import Admin
from util import render_html_template


class WebsiteMicroService(TechMicroService):
    DOC_MD = """
## Simple Flask website

Microservice to implement a small website with session.
"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

        self.register_blueprint(Admin(), url_prefix='/admin')
        self.register_blueprint(AccountBlueprint(LoginManager(self)), url_prefix='/account')

        @self.context_processor
        def inject_context():
            context = {
                "version": coworks_version
            }

            headers = {'Authorization': os.getenv('GITHUB_TOKEN')}
            resp = requests.get(os.getenv('COWORKS_GITHUB_URL'), headers=headers)
            if resp.ok:
                context["stargazers_count"] = resp.json()["stargazers_count"]

            return context

    @entry(no_auth=True)
    def get(self):
        """Entry for the home page."""
        data = {}
        headers = {'Accept': "application/json"}
        resp = requests.get(os.getenv('COWORKS_LAYERS_URL'), headers=headers)
        if resp.ok:
            layers_resp = resp.json()
            data['last_layer'] = layers_resp["last"]
            zip = layers_resp["last"].split(':')[-1].replace('_', '.')
            data['last_layer_url'] = f"https://coworks-layer.s3.eu-west-1.amazonaws.com/{zip}.zip"

        return render_html_template("home.j2", **data)

    @entry(no_auth=True)
    def get_assets_css(self, filename):
        """Access for all css files."""
        return send_from_directory('assets', f"css/{filename}", as_attachment=False, conditional=False)

    @entry(no_auth=True, binary=True)
    def get_assets_img(self, filename):
        """Access for all images."""
        return send_from_directory('assets', f"img/{filename}", as_attachment=False, conditional=False)

    @entry(no_auth=True, binary=True)
    def get_zip(self):
        """Access to the AirFlow plugins zip."""
        return send_from_directory('assets', "plugins.zip", as_attachment=True, conditional=False)


