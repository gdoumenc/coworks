from pathlib import Path
from unittest.mock import Mock

import boto3
from flask.cli import ScriptInfo

from coworks import Blueprint
from coworks import TechMicroService
from coworks import entry
from coworks.cws.deploy import TerraformLocal
from coworks.utils import import_attr


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

    @entry(binary=True, no_auth=True)
    def get_img(self):
        return b"image content"


class TestClass:

    def test_api_resources(self, example_dir, progressbar):
        app = TechMS()
        with app.test_request_context() as ctx:
            info = ScriptInfo(create_app=lambda _: app)
            terraform = TerraformLocal(info, progressbar, terraform_dir="terraform")
            ressources = terraform.api_resources
        assert len(ressources) == 7
        assert ressources[''].rules is not None
        assert len(ressources[''].rules) == 1
        assert not ressources[''].rules[0].cws_binary
        assert not ressources[''].rules[0].cws_no_auth
        assert len(ressources['img'].rules) == 1
        assert ressources['img'].rules[0].cws_binary
        assert ressources['img'].rules[0].cws_no_auth
        assert ressources['test'].rules is None
        assert ressources['test_index'].rules is not None
        assert len(ressources['test_index'].rules) == 1
        assert ressources['extended'].rules is None

    def test_deploy_ressources(self, example_dir, progressbar, capsys):
        app = import_attr('cmd', 'app', cwd=example_dir)
        info = ScriptInfo(create_app=lambda _: app)
        with app.test_request_context() as ctx:
            api_ressources = TerraformLocal(info, progressbar, terraform_dir=example_dir).api_resources
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

    def test__cmd(self, monkeypatch, example_dir, progressbar, capsys):
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
            info = ScriptInfo(create_app=lambda _: app)
            terraform = TerraformLocal(info, progressbar, terraform_dir=Path(example_dir) / "terraform")
            terraform.generate_files("deploy.j2", "test.tf", **options)
        with (Path(example_dir) / "terraform" / "test.tf").open() as f:
            lines = f.readlines()
        assert len(lines) == 2004
        assert lines[3].strip() == 'alias = "envtechms"'
        assert lines[21].strip() == 'envtechms_when_default = terraform.workspace == "default" ? 1 : 0'
        assert lines[22].strip() == 'envtechms_when_stage = terraform.workspace != "default" ? 1 : 0'
        (Path(example_dir) / "terraform" / "test.tf").unlink()
        (Path(example_dir) / "terraform").rmdir()
