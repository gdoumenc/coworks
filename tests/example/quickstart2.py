from coworks import TechMicroService
from coworks.cws.deployer import CwsTerraformDeployer
from coworks.cws.runner import CwsRunner


class SimpleMicroService(TechMicroService):

    def auth(self, auth_request):
        return True

    def get(self):
        return "Simple microservice ready.\n"


app = SimpleMicroService()
CwsRunner(app)
CwsTerraformDeployer(app, name='deploy')
