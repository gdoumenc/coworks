from coworks import TechMicroService
from coworks import entry


class SimpleMicroService(TechMicroService):

    @entry(no_auth=True)
    def get(self):
        return "Hello world.\n"


app = SimpleMicroService()
