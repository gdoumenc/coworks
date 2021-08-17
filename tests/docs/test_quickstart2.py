import threading
import time

import pytest
import requests

from coworks import aws
from coworks.cws.runner import ThreadedLocalServer
from coworks.utils import import_attr


import pytest
@pytest.mark.skip
class TestClass:

    def test_run_quickstart2(self, monkeypatch, s3_session, samples_docs_dir):
        monkeypatch.setattr(aws, "AwsS3Session", s3_session)
        app = import_attr('quickstart2', 'app', cwd=samples_docs_dir)
        port = ThreadedLocalServer.unused_tcp_port()
        server = threading.Thread(target=run_server_quickstart, args=(app, port, samples_docs_dir), daemon=True)
        server.start()
        counter = 1
        time.sleep(counter)
        while not server.is_alive() and counter < 10:
            time.sleep(counter)
            counter += 1
        response = requests.get(f'http://localhost:{port}/', headers={'Authorization': "token"})
        assert response.text == "Simple microservice ready.\n"

    def test_zip_quickstart2(self, monkeypatch, s3_session, samples_docs_dir):
        monkeypatch.setattr(aws, "AwsS3Session", s3_session)
        app = import_attr('quickstart2', 'app', cwd=samples_docs_dir)

        # without hash
        with pytest.raises(CwsCommandError):
            app.execute('zip', project_dir=samples_docs_dir, module='quickstart2', workspace='dev')
        app.execute('zip', project_dir=samples_docs_dir, module='quickstart2', workspace='dev',
                    profile_name='profile', bucket='bucket')
        assert len(s3_session.mock.method_calls) == 1
        name, params, _ = s3_session.mock.method_calls[0]
        assert name == 'client.upload_fileobj'
        assert params[1] == 'bucket'
        assert params[2] == 'quickstart2-simplemicroservice'

        # with hash
        with pytest.raises(CwsCommandError):
            app.execute('zip', project_dir=samples_docs_dir, module='quickstart2', workspace='dev')
        app.execute('zip', project_dir=samples_docs_dir, module='quickstart2', workspace='dev',
                    profile_name='profile', bucket='bucket', hash=True)
        assert len(s3_session.mock.method_calls) == 1 + 2
        name, params, _ = s3_session.mock.method_calls[0]
        assert name == 'client.upload_fileobj'
        assert params[1] == 'bucket'
        assert params[2] == 'quickstart2-simplemicroservice'


def run_server_quickstart(app, port, samples_docs_dir):
    print(f"Server starting on port {port}")
    app.execute('run', host='localhost', port=port, project_dir=samples_docs_dir, module='quickstart3', workspace='dev')
