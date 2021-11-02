import os
from unittest import mock
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

    @mock.patch.dict(os.environ, {"FLASK_APP": "complete:app"})
    def test_routes_command(self, monkeypatch, samples_docs_dir):
        mclick = Mock()
        monkeypatch.setattr(click, "echo", mclick)
        client.main(['--project-dir', samples_docs_dir, 'routes'], 'cws', standalone_mode=False)
        del os.environ["FLASK_RUN_FROM_CLI"]
        mclick.assert_any_call('admin_get_route    GET      /admin/route')
        mclick.assert_any_call('get                GET      /')
        mclick.assert_any_call('post               POST     /')
