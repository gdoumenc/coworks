import os

import pytest
from click import NoSuchOption
from click import UsageError
from flask.cli import ScriptInfo

from coworks.cws.client import client
from coworks.cws.deploy import Terraform
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

