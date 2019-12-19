import os

from coworks import TechMicroService
from coworks.blueprint.admin import Admin


class App(TechMicroService):

    def get(self):
        return os.getenv('test', False)


app = App(app_name="test")
app.register_blueprint(Admin('admin'))

if __name__ == '__main__':
    app.run()
