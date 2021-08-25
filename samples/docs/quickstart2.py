import click
from coworks import TechMicroService, entry
# from coworks.cws.deployer import CwsTerraformDeployer


class SimpleMicroService(TechMicroService):

    def token_authorizer(self, token):
        return True

    @entry
    def get(self):
        return "Simple microservice ready.\n"


app = SimpleMicroService()
# FLASK_APP=samples.docs.quickstart1:app flask deploy
