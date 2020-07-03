import io
import re

from coworks.cws import CwsTerraformWriter
from tests.src.coworks.tech_ms import SimpleMS


class TestClass:

    def test_export_terraform(self):
        simple = SimpleMS()
        writer = CwsTerraformWriter(simple)
        simple.commands['terraform'].execute(module="", service="", output='/dev/null', project_dir='.',
                                             workspace='dev', step='update', config=None)
        output = io.StringIO()
        writer.execute(module="", service="", output=output, project_dir='.', workspace='dev', step='update',
                       config=None)
        output.seek(0)
        print(output.read())
        output.seek(0)
        assert len(re.sub(r"\s", "", output.read())) == 18196
        print(writer.entries)
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
