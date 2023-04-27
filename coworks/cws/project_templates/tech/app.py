import os

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
        Migrate(self, db)
        """

    def token_authorizer(self, token):
        # Simple authorization process.
        # If you want to access AWS event or context for a more complex case, override the function _token_handler.
        return token in os.getenv('USER_KEYS').split(',')

    @entry
    def get(self):
        return 'project ready!\n'


app = MyMicroService()

# For this extension you need to install 'aws_xray_sdk'.
# XRay(app, xray_recorder)
