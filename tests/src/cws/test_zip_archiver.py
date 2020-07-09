from unittest.mock import Mock
from tests.src.coworks.tech_ms import SimpleMS
from coworks.cws.zip_archiver import CwsZipArchiver


class TestClass:

    def test_zip(self):
        simple_ms = SimpleMS()
        zip = CwsZipArchiver(simple_ms)
        zip.execute = Mock()
        simple_ms.execute(command='zip', project_dir='.', module='test', service='test', workspace='workspace',
                          profile_name='profile_name')
        zip.execute.assert_called_once()

        actual = zip.execute.call_args[1]["options"]
        expected = {'project_dir': '.', 'module': 'test', 'workspace': 'workspace', 'service': 'test', 'profile_name': 'profile_name'}

        assert len(set(actual.items()) - set(expected.items())) == 0
