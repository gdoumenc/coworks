from coworks import TechMicroService
from coworks.cws import CwsProject


class SimpleMicroService(TechMicroService):

    def get(self):
        return f"Simple microservice ready.\n"


app = SimpleMicroService()
CwsProject(app)
