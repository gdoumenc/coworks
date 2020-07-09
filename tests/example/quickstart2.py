from coworks import TechMicroService
from coworks.cws.runner import CwsRunner
from coworks.cws.deployer import CwsDeployer
from coworks.cws.writer import CwsTerraformStagingWriter
from coworks.config import Config

class SimpleMicroService(TechMicroService):

    def get(self):
        return f"Simple microservice ready.\n"

    def auth(self, auth_request):
        return auth_request.token == "token"

CONFIG = Config(
    workspace="dev"
)

app = SimpleMicroService(ms_name='test', configs=[CONFIG])
CwsRunner(app)
CwsTerraformStagingWriter(app)
CwsDeployer(app)