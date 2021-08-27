from coworks import TechMicroService
from coworks import entry


class SimpleMicroService(TechMicroService):

    def token_authorizer(self, token):
        return True

    @entry
    def get(self):
        return "Simple microservice ready.\n"


app = SimpleMicroService()

