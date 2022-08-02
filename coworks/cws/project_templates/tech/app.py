import os

from flask import request

from config import DevConfig
from config import LocalConfig
from config import ProdConfig
from coworks import TechMicroService
from coworks import entry
from coworks.blueprint.admin_blueprint import Admin
from coworks.blueprint.profiler_blueprint import Profiler


# from aws_xray_sdk.core import xray_recorder
# from coworks.middleware.xray import XRayMiddleware


class MyMicroService(TechMicroService):
    DOC_MD = """
## Microservice for ...
"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_blueprint(Admin(), url_prefix='/admin')
        self.register_blueprint(Profiler(), url_prefix='/profiler')

        # For this middleware you need to install 'aws_xray_sdk'.
        # XRayMiddleware(self, xray_recorder)

        @self.before_first_request
        def first():
            ...

        @self.before_request
        def before():
            ...

        @self.errorhandler(500)
        def handle(e):
            ...

    def init_app(self):
        user_key = os.getenv("USER_KEY")

    def token_authorizer(self, token):
        # Redefined to allow specific verification
        user_key = request.headers.get("USER_KEY")
        return token == os.getenv('TOKEN') and user_key is not None

    @entry
    def get(self):
        return 'project ready!\n'


local = LocalConfig()
local.environment_variables = {
    'LOCAL': 'my_value',
}
test = DevConfig('test')
dev = DevConfig()
prod = ProdConfig()
app = MyMicroService(configs=[local, test, dev, prod])
