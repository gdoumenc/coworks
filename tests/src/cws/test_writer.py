import io
import re

from coworks.config import Config, CORSConfig
from coworks.cws.writer import CwsTerraformWriter
from tests.src.coworks.tech_ms import SimpleMS


class TestClass:

    def test_export_terraform(self):
        simple = SimpleMS()
        writer = CwsTerraformWriter(simple)
        output = io.StringIO()
        self.export_cmd(simple, output)
        output.seek(0)
        print(output.read())
        output.seek(0)
        assert len(re.sub(r"\s", "", output.read())) == 8449
        assert len(writer.entries) == 8

        assert writer.entries['_'].parent_uid is None
        assert writer.entries['_'].is_root
        assert writer.entries['_'].path is None
        assert 'GET' in writer.entries['_'].methods
        assert 'POST' not in writer.entries['_'].methods

        assert writer.entries['__content'].parent_uid == '_'
        assert not writer.entries['__content'].is_root
        assert writer.entries['__content'].parent_is_root
        assert writer.entries['__content'].path == 'content'
        assert 'GET' in writer.entries['__content'].methods
        assert 'POST' in writer.entries['__content'].methods

        assert writer.entries['__extended'].methods is None

        assert not writer.entries['__extended_content'].is_root
        assert not writer.entries['__extended_content'].parent_is_root
        assert 'GET' in writer.entries['__extended_content'].methods

    def test_export_terraform_with_cors(self):
        config = Config(cors=CORSConfig(allow_origin='www.test.fr'))
        simple = SimpleMS(configs=config)
        CwsTerraformWriter(simple)
        output = io.StringIO()
        self.export_cmd(simple, output)
        output.seek(0)
        print(output.read())
        output.seek(0)
        assert len(re.sub(r"\s", "", output.read())) == 19606

    @staticmethod
    def export_cmd(simple, output):
        options = {'project_dir': '.', 'module': "test", 'workspace': 'dev', 'step': 'update'}
        simple.execute('terraform', output=output, **options)
