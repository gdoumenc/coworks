from coworks import TechMicroService


class SimpleMicroService(TechMicroService):

    def get(self):
        return f"Simple microservice ready.\n"


app = SimpleMicroService()
