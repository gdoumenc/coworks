from coworks import TechMicroService
from coworks.cws import CwsRunner, CwsProject


class SimpleMicroService(TechMicroService):

    def get(self):
        return f"Simple microservice ready.\n"

    def auth(self, auth_request):
        return auth_request.token == "token"


app = SimpleMicroService(ms_name='test')
CwsProject(app)
