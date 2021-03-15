from aws_xray_sdk.core import xray_recorder

from coworks import TechMicroService, entry
from coworks.config import Config
from coworks.context_manager import XRayContextManager
from coworks.cws.deployer import CwsTerraformDeployer
from coworks.cws.runner import CwsRunner


class SimpleMicroService(TechMicroService):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.value = 0

    def auth(self, auth_request):
        return auth_request.token == "token"

    @entry
    def get(self):
        return f"Stored value {self.value}.\n"

    @entry
    def post(self, value=None):
        if value is not None:
            self.value = value
        return f"Value stored ({value}).\n"


CONFIG = Config(workspace="dev")

app = SimpleMicroService(name="sample-first-microservice", configs=[CONFIG])
CwsRunner(app)
XRayContextManager(app, xray_recorder)

if __name__ == '__main__':
    app.execute('run')
