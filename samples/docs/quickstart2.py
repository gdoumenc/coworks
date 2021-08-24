import click
from coworks import TechMicroService, entry
# from coworks.cws.deployer import CwsTerraformDeployer


class SimpleMicroService(TechMicroService):

    def auth(self, auth_request):
        return True

    @entry
    def get(self):
        return "Simple microservice ready.\n"


app = SimpleMicroService()
# FLASK_APP=samples.docs.quickstart1:app flask deploy
