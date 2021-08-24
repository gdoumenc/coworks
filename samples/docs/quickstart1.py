from coworks import TechMicroService, entry


class SimpleMicroService(TechMicroService):

    def auth(self, auth_request):
        return True

    @entry
    def get(self):
        return "Simple microservice ready.\n"


app = SimpleMicroService()
# FLASK_APP=samples.docs.quickstart1:app flask run
