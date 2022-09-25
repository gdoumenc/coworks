from aws_xray_sdk.core import xray_recorder
from flask import render_template
from flask import send_from_directory

from coworks import TechMicroService
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

    @entry(no_auth=True)
    def get(self):
        """Entry for the home page."""
        headers = {'Content-Type': 'text/html; charset=utf-8'}
        return render_template("home.j2"), 200, headers

    @entry(no_auth=True)
    def get_assets(self, folder, filename):
        """Access for all assets."""
        return send_from_directory('assets', f"{folder}/{filename}", as_attachment=False)
