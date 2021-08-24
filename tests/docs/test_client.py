from pathlib import Path

import click
import os
from flask.cli import ScriptInfo
from unittest.mock import Mock

from coworks.cws.client import client
from coworks.cws.deployer import Terraform
from coworks.utils import import_attr


class TestClass:

    def test_default_command(self):
        assert 'run' in client.commands
        assert 'shell' in client.commands
        assert 'routes' in client.commands

    def test_routes_command(self, monkeypatch, samples_docs_dir):
        mclick = Mock()
        monkeypatch.setattr(click, "echo", mclick)
        app = import_attr('first', 'app', cwd=samples_docs_dir)
        obj = ScriptInfo(create_app=lambda _: app, set_debug_flag=False)
        client.main(['--project-dir', samples_docs_dir, 'routes'], 'cws', obj=obj, standalone_mode=False)
        del os.environ["FLASK_RUN_FROM_CLI"]
        mclick.assert_any_call('get       GET      /')
        mclick.assert_any_call('post      POST     /')

    def test_api_ressources(self, samples_docs_dir, capsys):
        app = import_attr('first', 'app', cwd=samples_docs_dir)
        with app.app_context() as ctx:
            api_ressources = Terraform(working_dir=samples_docs_dir).api_resources(app)
        assert len(api_ressources) == 1
        assert '' in api_ressources
        ter_resource = api_ressources['']
        assert len(ter_resource.rules) == 2
        # do not remove doc deployment
        # (Path(samples_docs_dir) / "terraform").rmdir()