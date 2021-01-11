import io
import threading
import time
from unittest.mock import MagicMock

import aws_xray_sdk.core as aws_xray_sdk
import requests

from coworks import aws
from coworks.cws.runner import ThreadedLocalServer
from coworks.utils import import_attr


class MockedXRaySession():
    mock = MagicMock()

    def capture(self, name):
        return lambda x: x

    def current_subsegment(self):
        return MockedXRaySession.mock


class TestClass:

    def test_run_first(self, monkeypatch, s3_session, example_dir):
        monkeypatch.setattr(aws, "AwsS3Session", s3_session)
        monkeypatch.setattr(aws_xray_sdk, "xray_recorder", MockedXRaySession())
        app = import_attr('first', 'app', cwd=example_dir)
        port = ThreadedLocalServer.unused_tcp_port()
        server = threading.Thread(target=run_server_quickstart, args=(app, port, example_dir), daemon=True)
        server.start()
        counter = 1
        time.sleep(counter)
        while not server.is_alive() and counter < 10:
            time.sleep(counter)
            counter += 1
        response = requests.get(f'http://localhost:{port}/', headers={'Authorization': "token"})
        assert response.text == "Stored value 0.\n"
        response = requests.post(f'http://localhost:{port}/', params={'value': 1}, headers={'Authorization': "token"})
        assert response.text == "Value stored.\n"
        response = requests.get(f'http://localhost:{port}/', headers={'Authorization': "token"})
        assert response.text == "Stored value 1.\n"

    def test_export_first(self, monkeypatch, s3_session, example_dir):
        monkeypatch.setattr(aws, "AwsS3Session", s3_session)
        app = import_attr('first', 'app', cwd=example_dir)
        output = io.StringIO()
        app.execute('export', project_dir=example_dir, module='first', workspace='dev', output=output)
        output.seek(0)
        print(output.read())


def run_server_quickstart(app, port, example_dir):
    print(f"Server starting on port {port}")
    app.execute('run', host='localhost', port=port, project_dir=example_dir, module='quickstart3', workspace='dev')
