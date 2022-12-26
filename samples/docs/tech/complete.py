from aws_xray_sdk.core import xray_recorder

from coworks import TechMicroService
from coworks import entry
from coworks.blueprint.admin_blueprint import Admin
from coworks.blueprint.profiler_blueprint import Profiler
from coworks.extension.xray import XRay


class SimpleMicroService(TechMicroService):
    DOC_MD = """
#### Microservice Documentation
You can document your CoWorks MicroService using the class attributes `DOC_MD` (markdown) or
the instance attributes `doc_md` (markdown) which gets rendered from the '/' entry of the admin blueprint.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_blueprint(Admin(), url_prefix='/admin')
        self.register_blueprint(Profiler(self), url_prefix='/profile')
        self.value = 0

    @entry
    def get(self):
        return f"Stored value {self.value}.\n"

    @entry
    def post(self, value=None):
        if value is not None:
            self.value = value
        return f"Value stored ({value}).\n"


app = SimpleMicroService(name="sample-complete-microservice")

XRay(app, xray_recorder)
