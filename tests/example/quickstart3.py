from coworks import TechMicroService
from coworks.config import Config, CORSConfig
from coworks.cws.writer import TerraformWriter


class SimpleMicroService(TechMicroService):

    def get(self):
        return f"Simple microservice ready.\n"

    def auth(self, auth_request):
        return auth_request.token == "token"


DEV_CONFIG = Config(
    cors=CORSConfig(allow_origin='*'),
    environment_variables_file="vars_dev.json"
)
PROD_CONFIG = Config(
    workspace="prod",
    cors=CORSConfig(allow_origin='www.mywebsite.com'),
    environment_variables_file="vars_prod.secret.json",
    version="0.0"
)

app = SimpleMicroService(app_name='test', configs=[DEV_CONFIG, PROD_CONFIG])
TerraformWriter(app)

if __name__ == '__main__':
    app.run(workspace='prod')
