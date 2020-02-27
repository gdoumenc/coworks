import os

from collections import defaultdict

from coworks import TechMicroService, BizMicroService, Every
from coworks.export import TerraformWriter
from coworks.blueprint import Admin


class TechApp(TechMicroService):
    """Technical microservice for the CoWorks tutorial example."""
    version = "1.2"
    values = defaultdict(int)

    def get(self, usage="test"):
        """Entrypoint for testing named parameter."""
        return f"Simple microservice for {usage}.\n"

    def get_value(self, index):
        """Entrypoint for testing positional parameter."""
        return f"{self.values[index]}\n"

    def put_value(self, index, value=0):
        self.values[index] = value
        return value

    def get_env(self):
        return f"Simple microservice for {os.getenv('test')}.\n"


class BizApp(BizMicroService):
    pass
    # def auth(self, auth_request):
    #     return True


app = tech_app = TechApp()
TerraformWriter(app)

biz_app = BizApp("stock_armony", app_name="ArmonyStock")
biz_app.register_blueprint(Admin())
# biz_app.react('test', Every(5, Every.MINUTES))

if __name__ == '__main__':
    biz_app.run(profile="fpr-customer")
