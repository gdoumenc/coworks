import threading
import time

import requests

from coworks.cws.runner import ThreadedLocalServer
from coworks.utils import import_attr


class TestClass:

    def test_run_first(self, monkeypatch, s3_session, samples_docs_dir):
        app = import_attr('first', 'app', cwd=samples_docs_dir)
        port = ThreadedLocalServer.unused_tcp_port()
        server = threading.Thread(target=run_server_quickstart, args=(app, port, samples_docs_dir), daemon=True)
        server.start()
        counter = 1
        time.sleep(counter)
        while not server.is_alive() and counter < 10:
            time.sleep(counter)
            counter += 1
        response = requests.get(f'http://localhost:{port}/', headers={'Authorization': "token"})
        assert response.text == "Stored value 0.\n"
        response = requests.post(f'http://localhost:{port}/', json={'value': 1}, headers={'Authorization': "token"})
        assert response.text == "Value stored (1).\n"
        response = requests.get(f'http://localhost:{port}/', headers={'Authorization': "token"})
        assert response.text == "Stored value 1.\n"


def run_server_quickstart(app, port, samples_docs_dir):
    print(f"Server starting on port {port}")
    app.execute('run', host='localhost', port=port, project_dir=samples_docs_dir, workspace='dev')
