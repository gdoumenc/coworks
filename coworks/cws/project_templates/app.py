import os

from aws_xray_sdk.core import xray_recorder
from coworks import TechMicroService
from coworks import entry
from coworks.blueprint.admin_blueprint import Admin
from coworks.blueprint.profiler_blueprint import Profiler
from coworks.middleware.xray import XRayMiddleware


class MyMicroService(TechMicroService):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_blueprint(Admin(), url_prefix='/admin')
        self.register_blueprint(Profiler(), url_prefix='/profiler')
        XRayMiddleware(self, xray_recorder)

    def token_authorizer(self, token):
        return token == 'test' # os.getenv('TOKEN')

    @entry
    def get(self):
        return 'project ready!'


app = MyMicroService()
