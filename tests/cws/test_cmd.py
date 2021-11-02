import os
from unittest import mock

import pytest
from click import NoSuchOption
from click import UsageError

from coworks.cws.client import client


class TestClass:

    @mock.patch.dict(os.environ, {"FLASK_APP": "cmd:app"})
    def test_wrong_project_dir(self, example_dir):
        with pytest.raises(UsageError) as pytest_wrapped_e:
            client.main(['--project-dir', 'doesntexist', 'test'], 'cws', standalone_mode=False)
            client(prog_name='cws', args=['-p', 'doesntexist', 'test'])
        assert pytest_wrapped_e.type == UsageError
        assert pytest_wrapped_e.value.args[0] == "No such command 'test'."

    def test_wrong_project_config_version(self, example_dir):
        with pytest.raises(RuntimeError) as pytest_wrapped_e:
            client.main(['--project-dir', example_dir, '--config-file-suffix', '.wrong.yml', 'cmd'], 'cws',
                        standalone_mode=False)
        assert pytest_wrapped_e.type == RuntimeError
        assert pytest_wrapped_e.value.args[0] == "Wrong project file version (should be 3).\n"

    def test_wrong_cmd(self, example_dir):
        with pytest.raises(UsageError) as pytest_wrapped_e:
            client.main(['--project-dir', example_dir, 'cmd'], 'cws', standalone_mode=False)
        assert pytest_wrapped_e.type == UsageError
        assert pytest_wrapped_e.value.args[0] == "No such command 'cmd'."

    @mock.patch.dict(os.environ, {"FLASK_APP": "cmd:app"})
    def test_cmd(self, example_dir, capsys):
        client.main(['--project-dir', example_dir, 'test'], 'cws', standalone_mode=False)
        captured = capsys.readouterr()
        assert captured.out == "test command with a=default/test command with b=value"

    def test_cmd_wrong_option(self, example_dir):
        with pytest.raises(NoSuchOption) as pytest_wrapped_e:
            client.main(['--project-dir', example_dir, 'test', '-t', 'wrong'], 'cws', standalone_mode=False)
        assert pytest_wrapped_e.type == NoSuchOption
        assert pytest_wrapped_e.value.args[0] == "No such option: -t"

    @mock.patch.dict(os.environ, {"FLASK_APP": "cmd:app"})
    def test_cmd_right_option(self, example_dir, capsys):
        client.main(['--project-dir', example_dir, 'test', '-a', 'right'], 'cws', standalone_mode=False)
        captured = capsys.readouterr()
        assert captured.out == "test command with a=right/test command with b=value"

    @mock.patch.dict(os.environ, {"FLASK_APP": "cmd:app"})
    def test_cmd_wrong_b_option(self, example_dir, capsys):
        with pytest.raises(NoSuchOption) as pytest_wrapped_e:
            client.main(['--project-dir', example_dir, 'test', '-b', 'right'], 'cws', standalone_mode=False)
        assert pytest_wrapped_e.type == NoSuchOption

    @mock.patch.dict(os.environ, {"FLASK_APP": "cmd:app"})
    def test_cmd_right_b_option(self, example_dir, capsys):
        try:
            client.main(['--project-dir', example_dir, 'test', '--b', 'right'], 'cws', standalone_mode=False)
        finally:
            os.unsetenv("FLASK_RUN_FROM_CLI")
        captured = capsys.readouterr()
        assert captured.out == "test command with a=default/test command with b=right"
