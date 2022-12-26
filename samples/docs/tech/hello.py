from coworks import TechMicroService
from coworks import entry


class HelloMicroService(TechMicroService):

    @entry(no_auth=True)
    def get(self):
        return "Hello world.\n"


app = HelloMicroService()
