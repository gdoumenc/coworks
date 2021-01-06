from coworks import TechMicroService
from coworks.cws.runner import CwsRunner


class SimpleMicroService(TechMicroService):

    def get(self):
        return "Simple microservice ready.\n"


app = SimpleMicroService()
CwsRunner(app)
