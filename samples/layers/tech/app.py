import os

import boto3
from aws_xray_sdk.core import xray_recorder

from config import DevConfig
from config import ProdConfig
from coworks import TechMicroService
from coworks import entry
from coworks.blueprint.admin_blueprint import Admin
from coworks.middleware.xray import XRayMiddleware


class CoworksLayersMicroService(TechMicroService):

    def __init__(self, **kwargs):
        super().__init__(name="cws_layers", **kwargs)
        self.register_blueprint(Admin(), url_prefix='/admin')
        XRayMiddleware(self, xray_recorder)
        self.lambda_client = None

    def init_app(self):
        access_key = os.getenv("KEY_ID")
        secret_key = os.getenv("SECRET_KEY")
        session = boto3.Session(access_key, secret_key, region_name='eu-west-1')
        self.lambda_client = session.client('lambda')

    @entry(no_auth=True)
    def get(self, full: bool = False):
        res = self.lambda_client.list_layers()
        layers = {l['LayerName']: l for l in filter(lambda x: x['LayerName'].startswith('coworks'), res['Layers'])}
        if full:
            return layers
        versions = [*filter(lambda x: 'dev' not in x, map(lambda x: x[8:].replace('_', '.'), layers))]
        versions.sort(key=lambda s: list(map(int, s.split('.'))))
        last_version = layers[f"coworks-{versions[-1].replace('.', '_')}"]
        return {
            'last': last_version['LayerArn'],
            'layers': [*map(lambda x: x['LayerArn'], layers.values())],
        }


def to_json(layers, full):
    if full:
        return {layer['LayerName']: layer for layer in layers}
    return {'coworks': [layer['LayerName'] for layer in layers]}


dev = DevConfig()
prod = ProdConfig()
app = CoworksLayersMicroService(configs=[dev, prod])
