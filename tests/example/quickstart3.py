from coworks import TechMicroService
from coworks.config import Config
from coworks.cws.runner import CwsRunner, run_with_reloader
from coworks.cws.writer import CwsTerraformWriter
from coworks.cws.zip import CwsZipArchiver


class SimpleMicroService(TechMicroService):

    def get(self):
        return f"Simple microservice ready.\n"

    def auth(self, auth_request):
        return auth_request.token == "token"


CONFIG = Config(
    workspace="dev"
)

app = SimpleMicroService(name='test', configs=[CONFIG])
CwsRunner(app)
CwsZipArchiver(app, name="upload")
CwsTerraformWriter(app, name='export')

if __name__ == '__main__':
    run_with_reloader(app, project_dir='.', module='quickstart1', workspace='dev')
