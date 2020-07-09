from unittest.mock import Mock
import pytest
from tests.src.coworks.tech_ms import SimpleMS
from coworks.cws.zip_archiver import CwsZipArchiver


@pytest.mark.wip
class TestClass:

    def test_zip(self):
        simple_ms = SimpleMS()
        CwsZipArchiver(simple_ms)
        CwsZipArchiver.execute = Mock()
        simple_ms.execute(command='zip', project_dir='.', module='test', service='test', workspace='workspace', profile_name='profile_name')
        CwsZipArchiver.execute.assert_called_once()
