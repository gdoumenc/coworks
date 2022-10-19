import os
from datetime import datetime

import boto3
from aws_xray_sdk.core import xray_recorder
from flask import render_template
from flask import url_for
from werkzeug.exceptions import BadRequest

from config import DevConfig
from config import ProdConfig
from coworks import TechMicroService
from coworks import entry
from coworks import request
from coworks.blueprint.admin_blueprint import Admin
from coworks.extension.xray import XRay


class CoworksLayersMicroService(TechMicroService):
    DOC_MD = """
## Layers service

Microservice to get all available CoWorks layers.
"""

    def __init__(self, **kwargs):
        super().__init__(name="cws_layers", **kwargs)
        self.register_blueprint(Admin(), url_prefix='/admin')
        XRay(self, xray_recorder)
        self.lambda_client = None

    def init_app(self):
        access_key = os.getenv("KEY_ID")
        secret_key = os.getenv("SECRET_KEY")
        if not access_key or not secret_key:
            raise BadRequest("Something wrong in your environment : no AWS credentials defined!")
        session = boto3.Session(access_key, secret_key, region_name='eu-west-1')
        self.lambda_client = session.client('lambda')

    @entry(no_auth=True)
    def get_home(self):
        """HTML page to get the layers."""
        headers = {'Content-Type': 'text/html; charset=utf-8'}
        return render_template('home.j2', url=url_for('get')), 200, headers

    @entry(no_auth=True)
    def get(self, full: bool = False):
        """Layers in json or text format."""
        res = self.lambda_client.list_layers()
        layers = {x['LayerName']: x for x in filter(lambda x: x['LayerName'].startswith('coworks'), res['Layers'])}
        if full:
            return layers
        versions = [*filter(lambda x: 'dev' not in x, map(lambda x: x[8:].replace('_', '.'), layers))]
        versions.sort(key=lambda s: list(map(int, s.split('.'))))
        last_version = layers[f"coworks-{versions[-1].replace('.', '_')}"]
        layers = map(lambda x: x['LayerArn'], layers.values())
        if request.accept_mimetypes['text/html']:
            return to_html(layers, last_version)
        return to_json(layers, last_version)


def to_json(layers, last_version):
    return {
        'last': last_version['LayerArn'],
        'layers': [*layers],
    }


def to_html(layers, last_version):
    data = {
        'layers': layers,
        'now': datetime.now(),
    }
    return render_template('layers.j2', **data), 200, {'Content-Type': 'text/html; charset=utf-8'}


app = CoworksLayersMicroService(configs=[DevConfig(), ProdConfig()])
