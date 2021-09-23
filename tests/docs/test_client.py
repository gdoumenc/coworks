import os
from unittest.mock import Mock

import click
from flask.cli import ScriptInfo

from coworks.cws.client import client
from coworks.utils import import_attr


class TestClass:

    def test_default_command(self):
        assert 'run' in client.commands
        assert 'shell' in client.commands
        assert 'routes' in client.commands

    def test_routes_command(self, monkeypatch, samples_docs_dir):
        mclick = Mock()
        monkeypatch.setattr(click, "echo", mclick)
        app = import_attr('complete', 'app', cwd=samples_docs_dir)
        obj = ScriptInfo(create_app=lambda _: app, set_debug_flag=False)
        client.main(['--project-dir', samples_docs_dir, 'routes'], 'cws', obj=obj, standalone_mode=False)
        del os.environ["FLASK_RUN_FROM_CLI"]
        mclick.assert_any_call('get           GET      /')
        mclick.assert_any_call('post          POST     /')
        mclick.assert_any_call('_get_route    GET      /admin/route')
