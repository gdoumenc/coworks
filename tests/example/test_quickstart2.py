import threading
import time
from unittest.mock import MagicMock

import pytest
import requests

from coworks import mixins
from coworks.cws.command import CwsCommandError
from coworks.cws.runner import ThreadedLocalServer
from coworks.utils import import_attr


class MockedAwsSession():
    mock = MagicMock()

    def __new__(cls, *args, **kwargs):
        return MockedAwsSession.mock


@pytest.mark.wip
class TestClass:

    def test_init(self, monkeypatch, example_dir):
        """Force to load the microservice with MockedAwsSession."""
        monkeypatch.setattr(mixins, "AwsS3Session", MockedAwsSession)
        import_attr('quickstart2', 'app', cwd=example_dir)

    def test_run_quickstart2(self, example_dir):
        app = import_attr('quickstart2', 'app', cwd=example_dir)
        port = ThreadedLocalServer.unused_tcp_port()
        server = threading.Thread(target=run_server_quickstart, args=(app, port, example_dir), daemon=True)
        server.start()
        counter = 1
        time.sleep(counter)
        while not server.is_alive() and counter < 3:
            time.sleep(counter)
            counter += 1
        response = requests.get(f'http://localhost:{port}/', headers={'Authorization': "token"})
        assert response.text == "Simple microservice ready.\n"

    def test_zip_quickstart2(self, example_dir):
        app = import_attr('quickstart2', 'app', cwd=example_dir)
        with pytest.raises(CwsCommandError):
            app.execute('upload', project_dir=example_dir, module='quickstart2', workspace='dev')
        app.execute('upload', project_dir=example_dir, module='quickstart2', workspace='dev',
                    profile_name='profile', bucket='bucket')
        assert len(MockedAwsSession.mock.method_calls) == 2
        name, params, _ = MockedAwsSession.mock.method_calls[0]
        assert name == 'client.upload_fileobj'
        assert params[1] == 'bucket'
        assert params[2] == 'quickstart2-simplemicroservice'


def run_server_quickstart(app, port, example_dir):
    print(f"Server starting on port {port}")
    app.execute('run', host='localhost', port=port, project_dir=example_dir, module='quickstart3', workspace='dev')
