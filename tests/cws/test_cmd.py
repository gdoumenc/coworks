import boto3
import os
import pytest
from click import NoSuchOption, UsageError
from flask.cli import ScriptInfo
from pathlib import Path
from unittest.mock import Mock

from coworks.cws.client import client
from coworks.cws.deployer import Terraform
from coworks.utils import import_attr


class TestClass:

    def test_wrong_project_dir(self, example_dir):
        with pytest.raises(RuntimeError) as pytest_wrapped_e:
            try:
                app = import_attr('cmd', 'app', cwd=example_dir)
                obj = ScriptInfo(create_app=lambda _: app, set_debug_flag=False)
                client.main(['--project-dir', 'doesntexist', 'test'], 'cws', obj=obj, standalone_mode=False)
            finally:
                os.unsetenv("FLASK_RUN_FROM_CLI")

            client(prog_name='cws', args=['-p', 'doesntexist', 'test'], obj={})
        assert pytest_wrapped_e.type == RuntimeError
        assert pytest_wrapped_e.value.args[0] == "Cannot find project file (project.cws.yml).\n"

    def test_wrong_project_config_version(self, example_dir):
        with pytest.raises(RuntimeError) as pytest_wrapped_e:
            try:
                client.main(['--project-dir', example_dir, '--config-file-suffix', '.wrong.yml', 'cmd'], 'cws',
                            standalone_mode=False)
            finally:
                os.unsetenv("FLASK_RUN_FROM_CLI")
        assert pytest_wrapped_e.type == RuntimeError
        assert pytest_wrapped_e.value.args[0] == "Wrong project file version (should be 3).\n"

    def test_wrong_cmd(self, example_dir):
        with pytest.raises(UsageError) as pytest_wrapped_e:
            try:
                client.main(['--project-dir', example_dir, 'cmd'], 'cws', standalone_mode=False)
            finally:
                os.unsetenv("FLASK_RUN_FROM_CLI")
        assert pytest_wrapped_e.type == UsageError
        assert pytest_wrapped_e.value.args[0] == "No such command 'cmd'."

    def test_cmd(self, example_dir, capsys):
        try:
            app = import_attr('cmd', 'app', cwd=example_dir)
            obj = ScriptInfo(create_app=lambda _: app, set_debug_flag=False)
            client.main(['--project-dir', example_dir, 'test'], 'cws', obj=obj, standalone_mode=False)
        finally:
            os.unsetenv("FLASK_RUN_FROM_CLI")
        captured = capsys.readouterr()
        assert captured.out == "test command with a=default/test command with b=value"

    def test_cmd_wrong_option(self, example_dir):
        with pytest.raises(NoSuchOption) as pytest_wrapped_e:
            try:
                client.main(['--project-dir', example_dir, 'test', '-t', 'wrong'], 'cws', standalone_mode=False)
            finally:
                os.unsetenv("FLASK_RUN_FROM_CLI")
        assert pytest_wrapped_e.type == NoSuchOption
        assert pytest_wrapped_e.value.args[0] == "No such option: -t"

    def test_cmd_right_option(self, example_dir, capsys):
        try:
            app = import_attr('cmd', 'app', cwd=example_dir)
            obj = ScriptInfo(create_app=lambda _: app, set_debug_flag=False)
            client.main(['--project-dir', example_dir, 'test', '-a', 'right'], 'cws', obj=obj, standalone_mode=False)
        finally:
            os.unsetenv("FLASK_RUN_FROM_CLI")
        captured = capsys.readouterr()
        assert captured.out == "test command with a=right/test command with b=value"

    def test_cmd_wrong_b_option(self, example_dir, capsys):
        with pytest.raises(NoSuchOption) as pytest_wrapped_e:
            try:
                app = import_attr('cmd', 'app', cwd=example_dir)
                obj = ScriptInfo(create_app=lambda _: app, set_debug_flag=False)
                client.main(['--project-dir', example_dir, 'test', '-b', 'right'], 'cws', obj=obj,
                            standalone_mode=False)
            finally:
                os.unsetenv("FLASK_RUN_FROM_CLI")
        assert pytest_wrapped_e.type == NoSuchOption

    def test_cmd_right_b_option(self, example_dir, capsys):
        try:
            app = import_attr('cmd', 'app', cwd=example_dir)
            obj = ScriptInfo(create_app=lambda _: app, set_debug_flag=False)
            client.main(['--project-dir', example_dir, 'test', '--b', 'right'], 'cws', obj=obj, standalone_mode=False)
        finally:
            os.unsetenv("FLASK_RUN_FROM_CLI")
        captured = capsys.readouterr()
        assert captured.out == "test command with a=default/test command with b=right"

    def test_api_ressources(self, example_dir, capsys):
        app = import_attr('cmd', 'app', cwd=example_dir)
        with app.test_request_context() as ctx:
            api_ressources = Terraform(working_dir=example_dir).api_resources(app)
        assert len(api_ressources) == 5
        assert '' in api_ressources
        assert 'init' in api_ressources
        assert 'env' in api_ressources
        assert 'value' in api_ressources
        assert 'value_index' in api_ressources
        ter_resource = api_ressources['']
        assert len(ter_resource.rules) == 1
        ter_resource = api_ressources['value_index']
        assert len(ter_resource.rules) == 2

    def test_deployer(self, monkeypatch, example_dir, capsys):
        monkeypatch.setattr(boto3, "Session", Mock(return_value=Mock(return_value='region')))
        app = import_attr('cmd', 'app', cwd=example_dir)
        config = app.get_config('workspace')
        with app.test_request_context() as ctx:
            options = {
                'project_dir': example_dir,
                'workspace': 'workspace',
                'debug': False,
                'profile_name': 'profile_name',
                'timeout': 30,
                'memory_size': 100,
            }
            terraform = Terraform(working_dir=Path(example_dir) / "terraform")
            info = ScriptInfo(create_app=lambda _:app)
            terraform.generate_files(info, config, "deploy.j2", "test.tf", **options)
        with (Path(example_dir) / "terraform" / "test.tf").open() as f:
            lines = f.readlines()
        assert len(lines) == 1665
        assert lines[3].strip() == 'envtechms_when_default = terraform.workspace == "default" ? 1 : 0'
        assert lines[4].strip() == 'envtechms_when_stage = terraform.workspace != "default" ? 1 : 0'
        (Path(example_dir) / "terraform" / "test.tf").unlink()
        (Path(example_dir) / "terraform").rmdir()
