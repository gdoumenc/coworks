import os
from unittest import mock
from unittest.mock import Mock

import click

from coworks.cws.client import client


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
        mclick.assert_called()
        assert len(mclick.mock_calls) == 7
        out = [call.args[0].split(' ')[0] for call in mclick.mock_calls]
        assert 'Endpoint' in str(mclick.mock_calls[0])
        assert '/admin/route_GET' in out
        assert '/_GET' in out
        assert '/_POST' in out
