import os

from flask import request

from coworks import TechMicroService
from coworks import entry
from coworks.blueprint.admin_blueprint import Admin
from coworks.blueprint.profiler_blueprint import Profiler
from coworks.utils import get_app_stage


# from aws_xray_sdk.core import xray_recorder
# from coworks.extension.xray import XRay


class MyMicroService(TechMicroService):
    DOC_MD = """
## Microservice for ...
"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.register_blueprint(Admin(), url_prefix='/admin')
        if get_app_stage() == "dev":
            self.register_blueprint(Profiler(self), url_prefix='/profiler')

        @self.before_request
        def before():
            ...

        @self.errorhandler(500)
        def handle(e):
            ...

    def init_cli(self):
        """
        from flask_migrate import Migrate
        Migrate(app, db)
        """

    def token_authorizer(self, token):
        # Redefined to allow specific verification
        user_key = request.headers.get("USER_KEY")
        return token == os.getenv('TOKEN') and user_key is not None

    @entry
    def get(self):
        return 'project ready!\n'


app = MyMicroService()

# For this extension you need to install 'aws_xray_sdk'.
# XRay(app, xray_recorder)
