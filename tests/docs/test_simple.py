import multiprocessing
import os
import time
from unittest import mock

import requests

from coworks.utils import import_attr


class TestClass:

    @mock.patch.dict(os.environ, {"WORKSPACE": "local"})
    @mock.patch.dict(os.environ, {"FLASK_RUN_FROM_CLI": "false"})
    def test_run_simple(self, samples_docs_dir, unused_tcp_port):
        app = import_attr('simple', 'app', cwd=samples_docs_dir)
        server = multiprocessing.Process(target=run_server, args=(app, unused_tcp_port), daemon=True)
        server.start()
        counter = 1
        time.sleep(counter)
        while not server.is_alive() and counter < 3:
            time.sleep(counter)
            counter += 1
        response = requests.get(f'http://localhost:{unused_tcp_port}/', headers={'Authorization': "token"})
        assert response.text == "Hello world.\n"
        server.terminate()


def run_server(app, port):
    print(f"Server starting on port {port}")
    app.run(host='localhost', port=port, use_reloader=False, debug=False)
