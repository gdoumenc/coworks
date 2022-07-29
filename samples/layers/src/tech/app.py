import os

import boto3
from aws_xray_sdk.core import xray_recorder

from config import DevConfig
from config import LocalConfig
from config import ProdConfig
from coworks import TechMicroService
from coworks import entry
from coworks.blueprint.admin_blueprint import Admin
from coworks.blueprint.profiler_blueprint import Profiler
from coworks.middleware.xray import XRayMiddleware


class CoworksLayersMicroService(TechMicroService):

    def __init__(self, **kwargs):
        super().__init__(name="cws_layers", **kwargs)
        self.register_blueprint(Admin(), url_prefix='/admin')
        self.register_blueprint(Profiler(), url_prefix='/profiler')
        XRayMiddleware(self, xray_recorder)
        self.lambda_client = None

    def init_app(self):
        access_key = os.getenv("KEY_ID")
        secret_key = os.getenv("SECRET_KEY")
        session = boto3.Session(access_key, secret_key, region_name='eu-west-1')
        self.lambda_client = session.client('lambda')

    @entry(no_auth=True)
    def get(self):
        res = self.lambda_client.list_layer_versions(LayerName="coworks-dev")
        return {
            'dev': res['LayerVersions']
        }


local = LocalConfig()
test = DevConfig('test')
dev = DevConfig()
prod = ProdConfig()
app = CoworksLayersMicroService(configs=[local, test, dev, prod])
