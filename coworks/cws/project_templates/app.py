import os

# from aws_xray_sdk.core import xray_recorder

from coworks import TechMicroService
from coworks import entry
from coworks.blueprint.admin_blueprint import Admin
from coworks.blueprint.profiler_blueprint import Profiler
from coworks.config import LocalConfig
from coworks.config import ProdConfig
# from coworks.middleware.xray import XRayMiddleware


class MyMicroService(TechMicroService):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_blueprint(Admin(), url_prefix='/admin')
        self.register_blueprint(Profiler(), url_prefix='/profiler')

        # For this middleware you need to install 'aws_xray_sdk'.
        # XRayMiddleware(self, xray_recorder)

        @self.before_first_request
        def first():
            var = int(os.getenv('VAR', 0))

        @self.before_request
        def before():
            ...

        @self.errorhandler(500)
        def handle(e):
            ...

    def token_authorizer(self, token):
        return token == os.getenv('TOKEN')

    @entry
    def get(self):
        return 'project ready!'


local = LocalConfig()
local.environment_variables = {
    'LOCAL': 'my_value',
}
prod = ProdConfig()
app = MyMicroService(configs=[local, prod])
