import multiprocessing
import os
import time
from unittest import mock

import requests

from coworks.utils import import_attr


class TestClass:
    @mock.patch.dict(os.environ, {"FLASK_RUN_FROM_CLI": "false", "AWS_XRAY_SDK_ENABLED": "false"})
    def test_run_first_no_token(self, samples_docs_dir, unused_tcp_port):
        app = import_attr('first', 'app', cwd=samples_docs_dir)
        server = multiprocessing.Process(target=run_server, args=(app, unused_tcp_port), daemon=True)
        server.start()
        counter = 1
        time.sleep(counter)
        while not server.is_alive() and counter < 10:
            time.sleep(counter)
            counter += 1
        response = requests.get(f'http://localhost:{unused_tcp_port}/')
        assert response.status_code == 401
        server.terminate()

    @mock.patch.dict(os.environ, {"FLASK_RUN_FROM_CLI": "false", "AWS_XRAY_SDK_ENABLED": "false"})
    def test_run_first_wrong_token(self, samples_docs_dir, unused_tcp_port):
        app = import_attr('first', 'app', cwd=samples_docs_dir)
        server = multiprocessing.Process(target=run_server, args=(app, unused_tcp_port), daemon=True)
        server.start()
        counter = 1
        time.sleep(counter)
        while not server.is_alive() and counter < 10:
            time.sleep(counter)
            counter += 1
        response = requests.get(f'http://localhost:{unused_tcp_port}/', headers={'Authorization': 'wrong'})
        assert response.status_code == 403

    @mock.patch.dict(os.environ, {"FLASK_RUN_FROM_CLI": "false", "AWS_XRAY_SDK_ENABLED": "false"})
    def test_run_first(self, samples_docs_dir, unused_tcp_port):
        app = import_attr('first', 'app', cwd=samples_docs_dir)
        server = multiprocessing.Process(target=run_server, args=(app, unused_tcp_port), daemon=True)
        server.start()
        counter = 1
        time.sleep(counter)
        while not server.is_alive() and counter < 10:
            time.sleep(counter)
            counter += 1
        response = requests.get(f'http://localhost:{unused_tcp_port}/', headers={'Authorization': "token"})
        assert response.text == "Stored value 0.\n"
        response = requests.post(f'http://localhost:{unused_tcp_port}/', json={'value': 1},
                                 headers={'Authorization': "token"})
        assert response.text == "Value stored (1).\n"
        response = requests.get(f'http://localhost:{unused_tcp_port}/', headers={'Authorization': "token"})
        assert response.text == "Stored value 1.\n"
        server.terminate()


def run_server(app, port):
    print(f"Server starting on port {port}")
    app.run(host='localhost', port=port, use_reloader=False, debug=False)
