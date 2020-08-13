from coworks import TechMicroService
from coworks.config import Config
from coworks.cws.runner import CwsRunner
from coworks.cws.writer import CwsTerraformWriter


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
CwsTerraformWriter(app, name='export')
