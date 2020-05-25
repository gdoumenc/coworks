from coworks import TechMicroService
from coworks.cws.writer import TerraformWriter


class SimpleMicroService(TechMicroService):

    def get(self):
        return f"Simple microservice ready.\n"

    def auth(self, auth_request):
        return auth_request.token == "token"


app = SimpleMicroService(app_name='test')
TerraformWriter(app)
