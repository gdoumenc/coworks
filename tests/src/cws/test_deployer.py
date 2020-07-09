from unittest.mock import Mock

from coworks.cws.writer import CwsTerraformStagingWriter
from tests.src.coworks.tech_ms import SimpleMS
from coworks.cws.deployer import CwsDeployer, CwsDestroyer
from coworks.cws.zip_archiver import CwsZipArchiver

class TestClass:

    def test_deploy(self):
        simple_ms = SimpleMS()
        CwsTerraformStagingWriter(simple_ms)
        CwsZipArchiver(simple_ms)
        CwsDeployer(simple_ms)
        CwsDeployer._local_deploy = Mock()
        simple_ms.execute(command='deploy', project_dir='.', module='test', service='test', workspace='dev', customer='customer', dry=True)
        CwsDeployer._local_deploy.assert_called_once()

    def test_destroy(self):
        simple_ms = SimpleMS()
        CwsTerraformStagingWriter(simple_ms)
        CwsDestroyer(simple_ms)
        CwsDestroyer._local_destroy = Mock()
        simple_ms.execute(command='destroy', project_dir='.', module='test', service='test', workspace='dev', customer='customer', dry=True)
        CwsDestroyer._local_destroy.assert_called_once()
