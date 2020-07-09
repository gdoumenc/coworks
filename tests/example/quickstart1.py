from coworks import TechMicroService
from coworks.cws.runner import CwsRunner


class SimpleMicroService(TechMicroService):

    def get(self):
        return f"Simple microservice ready.\n"


app = SimpleMicroService()
CwsRunner(app)
