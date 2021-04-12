from coworks import TechMicroService, entry
from coworks.config import Config
from coworks.cws.deployer import CwsTerraformDeployer
from coworks.cws.runner import CwsRunner


class SimpleMicroService(TechMicroService):

    def auth(self, auth_request):
        return True

    @entry
    def get(self):
        return "Simple microservice ready.\n"


app = SimpleMicroService(configs=Config())
CwsRunner(app)
CwsTerraformDeployer(app, name='deploy')
