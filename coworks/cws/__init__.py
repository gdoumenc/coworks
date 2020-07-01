from .writer import CwsTerraformWriter
from .writer import CwsTerraformStagingWriter
from .runner import CwsRunner
from .deployer import CwsDeployer


class CwsProject():

    def __init__(self, app=None):
        CwsRunner(app)
        CwsTerraformWriter(app, name='export')
        CwsDeployer(app)

