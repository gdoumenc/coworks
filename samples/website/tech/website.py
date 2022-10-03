import os

import requests
from aws_xray_sdk.core import xray_recorder
from flask import render_template
from flask import send_from_directory

from coworks import TechMicroService
from coworks import __version__ as coworks_version
from coworks import entry
from coworks.blueprint.admin_blueprint import Admin
from coworks.extension.xray import XRay


class WebsiteMicroService(TechMicroService):
    DOC_MD = """
## Simple Flask website

Microservice to implement a small website with session.
"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_blueprint(Admin(), url_prefix='/admin')
        XRay(self, xray_recorder)

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

        headers = {'Content-Type': 'text/html; charset=utf-8'}
        return render_template("home.j2", **data), 200, headers

    @entry(no_auth=True)
    def get_assets(self, folder, filename):
        """Access for all assets."""
        return send_from_directory('assets', f"{folder}/{filename}", as_attachment=False)
