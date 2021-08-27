import io
from werkzeug.middleware.profiler import ProfilerMiddleware

from coworks import TechMicroService
from coworks import entry
from coworks.blueprint import Admin

class SimpleMicroService(TechMicroService):

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

# FLASK_APP=samples.docs.complete:app cws run
# FLASK_APP=samples.docs.complete:app cws deploy
