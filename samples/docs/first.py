from coworks import TechMicroService
from coworks import entry


class SimpleMicroService(TechMicroService):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.value = 0

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


app = SimpleMicroService(name="sample-first-microservice")

# FLASK_APP=samples.docs.first:app cws run
# FLASK_APP=samples.docs.first:app cws deploy
