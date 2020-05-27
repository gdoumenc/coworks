import io
import json
import os
import tempfile

import pytest

from coworks.cws.client import client

EXAMPLE_DIR = os.getenv('EXAMPLE_DIR')


class TestClass:

    def test_init(self):
        with tempfile.TemporaryDirectory() as tmp:
            chalice_dir = os.path.join(tmp, '.chalice')

            with pytest.raises(SystemExit) as pytest_wrapped_e:
                client(prog_name='cws', args=['-p', tmp, 'init'], obj={})
            assert pytest_wrapped_e.type == SystemExit
            assert pytest_wrapped_e.value.code == 0

            assert os.path.exists(chalice_dir)
            assert os.path.exists(f"{chalice_dir}/config.json")

    def test_info(self):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', EXAMPLE_DIR, 'info'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1

        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', EXAMPLE_DIR, 'info', '-m', 'quickstart2'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0

        with pytest.raises(SystemExit) as pytest_wrapped_e:
            output = io.StringIO()
            client(prog_name='cws', args=['-p', EXAMPLE_DIR, 'info', '-m', 'quickstart2', '-o', output], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
        output.seek(0)
        out = json.loads(output.read())
        assert 'name' in out
        assert out['name'] == "test"
        assert 'type' in out
        assert out['type'] == "tech"

        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', EXAMPLE_DIR, 'info', '-m', 'example', '-a', 'test'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1

        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', EXAMPLE_DIR, 'info', '-m', 'example', '-a', 'tech_app'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0

    def test_export(self):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', EXAMPLE_DIR, 'export', '-m', 'example', '-a', 'tech_app'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
