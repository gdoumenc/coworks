import os
import tempfile
from pathlib import Path
from unittest import mock

import boto3
from flask.cli import ScriptInfo

from coworks import Blueprint
from coworks import TechMicroService
from coworks import entry
from coworks.cws.deploy import Terraform
from coworks.cws.deploy import TerraformContext
from coworks.cws.client import CwsScriptInfo
from coworks.cws.deploy import TerraformBackend


class CliCtxMokup:
    def find_root(self):
        return self

    @property
    def params(self):
        return {'project_dir': "."}


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
            terraform_context = TerraformContext(info, CliCtxMokup())
            backend = TerraformBackend(terraform_context, None, terraform_dir=".", terraform_refresh=False)
            terraform = Terraform(backend, terraform_dir="terraform", stage="common")
            api_ressources = terraform.api_resources
        assert len(api_ressources) == 7
        assert api_ressources[''].rules is not None
        assert len(api_ressources[''].rules) == 1
        assert not api_ressources[''].rules[0].cws_binary_headers
        assert not api_ressources[''].rules[0].cws_no_auth
        assert len(api_ressources['img'].rules) == 1
        assert api_ressources['img'].rules[0].cws_binary_headers
        assert api_ressources['img'].rules[0].cws_no_auth
        assert api_ressources['test'].rules is None
        assert api_ressources['test_index'].rules is not None
        assert len(api_ressources['test_index'].rules) == 1
        assert api_ressources['extended'].rules is None

    @mock.patch.dict(os.environ, {"test": "local", "FLASK_RUN_FROM_CLI": "true"})
    def test_deploy_ressources(self, example_dir, progressbar, capsys):
        info = CwsScriptInfo(project_dir='.')
        info.app_import_path = "command:app"
        app = info.load_app()
        with app.test_request_context() as ctx:
            info = ScriptInfo(create_app=lambda: app)
            terraform_context = TerraformContext(info, CliCtxMokup())
            backend = TerraformBackend(terraform_context, None, terraform_dir=".", terraform_refresh=False)
            terraform = Terraform(backend, terraform_dir="terraform", stage="common")
            api_ressources = terraform.api_resources
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
    def test_deploy_local_cmd(self, monkeypatch, example_dir, progressbar, capsys):
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
            terraform_context = TerraformContext(info, CliCtxMokup())
            backend = TerraformBackend(terraform_context, None, terraform_dir=".", terraform_refresh=False)
            terraform = Terraform(backend, terraform_dir=Path("terraform"), stage="common")
            with tempfile.NamedTemporaryFile() as fp:
                terraform.generate_file("deploy.j2", fp.name, **options)
                fp.seek(0)
                lines = fp.readlines()
                assert len(lines) == 2049
                assert lines[1].strip() == 'alias = "envtechms"'.encode('utf-8')

    @mock.patch.dict(os.environ, {"test": "local", "FLASK_RUN_FROM_CLI": "true"})
    def test_deploy_remote_cmd(self, monkeypatch, example_dir, progressbar, capsys):
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
                'terraform_cloud': True,
                'terraform_organization': "CoWorks",
            }
            info = ScriptInfo(create_app=lambda: app)
            terraform_context = TerraformContext(info, CliCtxMokup())
            backend = TerraformBackend(terraform_context, None, terraform_dir=".", terraform_refresh=False)
            terraform = Terraform(backend, terraform_dir=Path("terraform"), stage="common")
            with tempfile.NamedTemporaryFile() as fp:
                terraform.generate_file("terraform.j2", fp.name, **options)
                fp.seek(0)
                lines = fp.readlines()
                assert len(lines) == 43
                print(lines)
                assert "TERRAFORM ON CLOUD" in lines[1].decode('utf-8')
                assert "CoWorks" in lines[6].decode('utf-8')

    @mock.patch.dict(os.environ, {"test": "local", "FLASK_RUN_FROM_CLI": "true"})
    def test_destroy_cmd(self, monkeypatch, example_dir, progressbar, capsys):
        monkeypatch.setattr(boto3, "Session", mock.Mock(return_value=mock.Mock(return_value='region')))
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
            terraform_context = TerraformContext(info, CliCtxMokup())
            backend = TerraformBackend(terraform_context, None, terraform_dir=".", terraform_refresh=False)
            terraform = Terraform(backend, terraform_dir=Path("terraform"), stage="common")
            with tempfile.NamedTemporaryFile() as fp:
                terraform.generate_file("deploy.j2", fp.name, **options)
                fp.seek(0)
                lines = fp.readlines()
                assert len(lines) == 2049
                assert lines[1].strip() == 'alias = "envtechms"'.encode('utf-8')
