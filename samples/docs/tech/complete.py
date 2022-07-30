import io
from aws_xray_sdk.core import xray_recorder
from werkzeug.middleware.profiler import ProfilerMiddleware

from coworks import TechMicroService
from coworks import entry
from coworks.blueprint.admin_blueprint import Admin
from coworks.middleware.xray import XRayMiddleware


class SimpleMicroService(TechMicroService):
    DOC_MD = """
#### Microservice Documentation
You can document your CoWorks MicroService using the class attributes `DOC_MD` (markdown) or
the instance attributes `doc_md` (markdown) which gets rendered from the '/' entry of the admin blueprint.

![img](https://coworks.readthedocs.io/en/master/_images/coworks.png)
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.value = 0
        self.output = io.StringIO()

    def token_authorizer(self, token):
        return token == "token"

    @entry
    def get(self):
        return f"Stored value {self.value}.\n"

    @entry
    def post(self, value=None):
        if value is not None:
            self.value = value
        return f"Value stored ({value}).\n"

    @entry
    def get_profile(self):
        profile = self.output.getvalue()
        self.output.seek(0)
        return profile


app = SimpleMicroService(name="sample-complete-microservice")
app.register_blueprint(Admin(), url_prefix='/admin')

app.wsgi_app = ProfilerMiddleware(app.wsgi_app, stream=app.output)
XRayMiddleware(app, xray_recorder)
