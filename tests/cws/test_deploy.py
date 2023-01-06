import os
from pathlib import Path
from unittest.mock import Mock

import boto3
import mock
from flask.cli import ScriptInfo

from coworks import Blueprint
from coworks import TechMicroService
from coworks import entry
from coworks.cws.deploy import TerraformContext
from coworks.cws.deploy import TerraformLocal
from cws.client import CwsScriptInfo


class BP(Blueprint):

    @entry
    def get_test(self, index):
        return f"blueprint {self} {index}"

    @entry
    def get_extended_test(self, index):
        return f"blueprint extended test {index}"


class TechMS(TechMicroService):
    def __init__(self, **kwargs):
        super().__init__('test', **kwargs)
        self.register_blueprint(BP())

    def token_authorizer(self, token):
        return True

    @entry
    def get(self):
        return "simple get"

    @entry(binary_headers={'content-type': 'img/webp'}, no_auth=True)
    def get_img(self):
        return b"image content"


class TestClass:

    def test_api_resources(self, example_dir, progressbar):
        app = TechMS()
        with app.test_request_context() as ctx:
            info = ScriptInfo(create_app=lambda: app)
            app_context = TerraformContext(info)
            terraform = TerraformLocal(app_context, progressbar, terraform_dir="terraform")
            ressources = terraform.api_resources
        assert len(ressources) == 7
        assert ressources[''].rules is not None
        assert len(ressources[''].rules) == 1
        assert not ressources[''].rules[0].cws_binary_headers
        assert not ressources[''].rules[0].cws_no_auth
        assert len(ressources['img'].rules) == 1
        assert ressources['img'].rules[0].cws_binary_headers
        assert ressources['img'].rules[0].cws_no_auth
        assert ressources['test'].rules is None
        assert ressources['test_index'].rules is not None
        assert len(ressources['test_index'].rules) == 1
        assert ressources['extended'].rules is None

    @mock.patch.dict(os.environ, {"test": "local", "FLASK_RUN_FROM_CLI": "true"})
    def test_deploy_ressources(self, example_dir, progressbar, capsys):
        info = CwsScriptInfo(project_dir='.')
        info.app_import_path = "command:app"
        app = info.load_app()
        with app.test_request_context() as ctx:
            info = ScriptInfo(create_app=lambda: app)
            app_context = TerraformContext(info)
            api_ressources = TerraformLocal(app_context, progressbar, terraform_dir='.').api_resources
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

    @mock.patch.dict(os.environ, {"test": "local", "FLASK_RUN_FROM_CLI": "true"})
    def test_deploy_cmd(self, monkeypatch, example_dir, progressbar, capsys):
        info = CwsScriptInfo(project_dir='.')
        info.app_import_path = "command:app"
        app = info.load_app()
        with app.test_request_context() as ctx:
            options = {
                'project_dir': example_dir,
                'workspace': 'workspace',
                'debug': False,
                'timeout': 30,
                'memory_size': 100,
                'deploy': True,
            }
            info = ScriptInfo(create_app=lambda: app)
            app_context = TerraformContext(info)
            terraform = TerraformLocal(app_context, progressbar, terraform_dir="terraform")
            terraform.generate_files("deploy.j2", "test.tf", **options)
        with (Path("terraform") / "test.tf").open() as f:
            lines = f.readlines()
        assert len(lines) == 2280
        print(lines[20:25])
        assert lines[1].strip() == 'alias = "envtechms"'
        assert lines[21].strip() == 'envtechms_when_default = terraform.workspace == "default" ? 1 : 0'
        assert lines[22].strip() == 'envtechms_when_stage = terraform.workspace != "default" ? 1 : 0'
        (Path("terraform") / "test.tf").unlink()
        Path("terraform").rmdir()

    @mock.patch.dict(os.environ, {"test": "local", "FLASK_RUN_FROM_CLI": "true"})
    def test_destroy_cmd(self, monkeypatch, example_dir, progressbar, capsys):
        monkeypatch.setattr(boto3, "Session", Mock(return_value=Mock(return_value='region')))
        info = CwsScriptInfo(project_dir='.')
        info.app_import_path = "command:app"
        app = info.load_app()
        with app.test_request_context() as ctx:
            options = {
                'project_dir': example_dir,
                'workspace': 'workspace',
                'debug': False,
                'timeout': 30,
                'memory_size': 100,
                'deploy': False,
            }
            info = ScriptInfo(create_app=lambda: app)
            app_context = TerraformContext(info)
            terraform = TerraformLocal(app_context, progressbar, terraform_dir="terraform")
            terraform.generate_files("deploy.j2", "test.tf", **options)
        with (Path("terraform") / "test.tf").open() as f:
            lines = f.readlines()
        assert len(lines) == 2280
        print(lines[20:25])
        assert lines[1].strip() == 'alias = "envtechms"'
        assert lines[21].strip() == 'envtechms_when_default = terraform.workspace == "default" ? 0 : 0'
        assert lines[22].strip() == 'envtechms_when_stage = terraform.workspace != "default" ? 0 : 0'
        (Path("terraform") / "test.tf").unlink()
        Path("terraform").rmdir()
