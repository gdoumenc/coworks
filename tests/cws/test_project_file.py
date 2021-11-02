import os
from unittest import mock

import pytest

from coworks.cws.client import client


class TestClass:
    @mock.patch.dict(os.environ, {"FLASK_APP": "cmd:app"})
    def test_no_project_file_no_module(self, example_dir, capsys):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['--project-dir', example_dir, 'test'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0

    @pytest.mark.skip
    def test_project_file_no_param(self, example_dir, capsys):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', example_dir, 'test'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        # assert pytest_wrapped_e.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == \
               "test command with a=default/test command with b=valuetest command with a=project2/test command with b=value"

    @pytest.mark.skip
    def test_project_file_no_param_workspace_dev(self, example_dir, capsys):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', example_dir, '-w', 'dev', 'test'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == \
               "test command with a=default/test command with b=value"" +" \
               "test command with a=project2/test command with b=value"

    @pytest.mark.skip
    def test_project_file_no_param_workspace_prod(self, example_dir, capsys):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', example_dir, '-w', 'prod', 'test'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == \
               "test command with a=default/test command with b=valuetest command with a=prod2/test command with b=value"

    @pytest.mark.skip
    def test_project_file_param(self, example_dir, capsys):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', example_dir, 'test', '-a', 'param'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == \
               "test command with a=param/test command with b=valuetest command with a=param/test command with b=value"

    @pytest.mark.skip
    def test_project_file_project1(self, example_dir, capsys):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', example_dir, '-m', 'example', '-s', 'project1', 'test'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == "test command with a=default/test command with b=value"

    @pytest.mark.skip
    def test_project_file_project2(self, example_dir, capsys):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', example_dir, '-m', 'example', '-s', 'project2', 'test'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == "test command with a=project2/test command with b=value"
