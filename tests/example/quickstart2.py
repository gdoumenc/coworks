from coworks import TechMicroService
from coworks.cws.runner import CwsRunner
from coworks.cws.zip import CwsZipArchiver
from coworks.cws.writer import CwsTemplateWriter


class SimpleMicroService(TechMicroService):

    def get(self):
        return f"Simple microservice ready.\n"


app = SimpleMicroService()
CwsRunner(app)
CwsZipArchiver(app)
CwsTemplateWriter(app)
