import io
import re

from coworks.config import Config, CORSConfig
from coworks.cws.deployer import CwsTerraformDeployer
from tests.coworks.tech_ms import SimpleMS


class TestClass:

    def test_export_terraform(self):
        simple = SimpleMS()
        writer = CwsTerraformDeployer(simple)
        output = io.StringIO()
        self.export_cmd(simple, output)
        output.seek(0)
        print(output.read())
        output.seek(0)
        assert len(re.sub(r"\s", "", output.read())) == 44
        assert len(simple.entries) == 7

        assert 'GET' in simple.entries['']
        assert 'POST' not in simple.entries['']
        assert writer.terraform_api_resources(simple)[''].parent_uid is None
        assert writer.terraform_api_resources(simple)[''].is_root
        assert writer.terraform_api_resources(simple)[''].path is None

        assert 'GET' in simple.entries['content']
        assert 'POST' in simple.entries['content']
        assert writer.terraform_api_resources(simple)['content'].parent_uid == ''
        assert not writer.terraform_api_resources(simple)['content'].is_root
        assert writer.terraform_api_resources(simple)['content'].parent_is_root
        assert writer.terraform_api_resources(simple)['content'].path == 'content'

        assert 'GET' in simple.entries['extended/content']
        assert 'POST' not in simple.entries['extended/content']
        assert 'extended' not in simple.entries
        assert not writer.terraform_api_resources(simple)['extended'].is_root
        assert writer.terraform_api_resources(simple)['extended'].path == 'extended'
        assert writer.terraform_api_resources(simple)['extended'].entries is None

        assert 'GET' in simple.entries['kwparam1']
        assert 'POST' not in simple.entries['kwparam1']
        assert 'GET' in simple.entries['kwparam2']
        assert 'POST' not in simple.entries['kwparam2']

    def test_export_terraform_with_cors(self):
        config = Config(cors=CORSConfig(allow_origin='www.test.fr'))
        simple = SimpleMS(configs=config)
        CwsTerraformDeployer(simple)
        output = io.StringIO()
        self.export_cmd(simple, output)
        output.seek(0)
        print(output.read())
        output.seek(0)
        assert len(re.sub(r"\s", "", output.read())) == 44

    @staticmethod
    def export_cmd(simple, output):
        options = {'project_dir': 'tests/cws', 'module': "test", 'workspace': 'dev', 'step': 'update'}
        simple.execute('export', output=output, **options)
