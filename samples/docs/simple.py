from coworks import TechMicroService
from coworks import entry


class SimpleMicroService(TechMicroService):

    @entry
    def get(self):
        return "Hello world.\n"


app = SimpleMicroService()
app.any_token_authorized = True

