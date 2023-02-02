import os
from unittest import mock

import pytest
from click import UsageError

from coworks.cws.client import client


class TestClass:
    @mock.patch.dict(os.environ, {"FLASK_APP": "command:app"})
    def test_no_project_file_no_module(self, capsys):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['--project-dir', '.', 'test'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0

    @mock.patch.dict(os.environ, {"FLASK_APP": "command:app"})
    def test_wrong_project_dir(self, example_dir):
        with pytest.raises(UsageError) as pytest_wrapped_e:
            client.main(['--project-dir', 'doesntexist', 'test'], 'cws', standalone_mode=False)
        msg = "Project dir /home/gdo/workspace/coworks/tests/cws/src/doesntexist not found."
        assert pytest_wrapped_e.value.args[0] == msg
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', 'doesntexist', 'test'])

    def test_wrong_project_config_version(self, example_dir):
        with pytest.raises(RuntimeError) as pytest_wrapped_e:
            client.main(['--project-dir', '.', '--config-file-suffix', '.wrong.yml', 'cmd'], 'cws',
                        standalone_mode=False)
        assert pytest_wrapped_e.type == RuntimeError
        assert pytest_wrapped_e.value.args[0] == "Wrong project file version (should be 3).\n"
