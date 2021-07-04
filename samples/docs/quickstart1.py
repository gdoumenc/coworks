from coworks import TechMicroService, entry
from coworks.cws.runner import CwsRunner


class SimpleMicroService(TechMicroService):

    def auth(self, auth_request):
        return True

    @entry
    def get(self):
        return "Simple microservice ready.\n"


app = SimpleMicroService()
CwsRunner(app)
