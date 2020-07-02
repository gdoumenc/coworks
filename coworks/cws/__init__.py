from .writer import CwsTerraformWriter, CwsTerraformStagingWriter
from .zip_archiver import CwsZipArchiver
from .runner import CwsRunner
from .deployer import CwsDeployer


class CwsProject:

    def __init__(self, app=None):
        CwsRunner(app)
        CwsZipArchiver(app)
        CwsTerraformWriter(app, name='export')
        CwsDeployer(app)

