import os
import threading
import time
from pathlib import Path

import requests

from coworks.config import Config
from coworks.cws.client import CwsCLIFactory
from coworks.pytest.local_server import ThreadedLocalServer
from .example import TechMS

EXAMPLE_DIR = os.getenv('EXAMPLE_DIR')


class TestClass:

    def test_simple_example(self, local_server_factory):
        local_server = local_server_factory(TechMS())
        response = local_server.make_call(requests.get, '/')
        assert response.status_code == 200
        assert response.text == "Simple microservice for test.\n"
        response = local_server.make_call(requests.get, '/', params={"usage": "demo"})
        assert response.status_code == 200
        assert response.text == "Simple microservice for demo.\n"
        response = local_server.make_call(requests.get, '/value/1')
        assert response.status_code == 200
        assert response.text == "0\n"
        response = local_server.make_call(requests.put, '/value/1', json={"value": 456})
        assert response.status_code == 200
        assert response.text == "456"
        response = local_server.make_call(requests.get, '/value/1')
        assert response.status_code == 200
        assert response.text == "456\n"

    def test_params(self, local_server_factory):
        local_server = local_server_factory(TechMS())
        response = local_server.make_call(requests.put, '/value/1', json=456)
        assert response.status_code == 200
        assert response.text == "456"
        response = local_server.make_call(requests.get, '/value/1')
        assert response.status_code == 200
        assert response.text == "456\n"

    def test_env(self, local_server_factory):
        config = Config(environment_variables_file=Path(EXAMPLE_DIR) / "_dev_vars.json")
        local_server = local_server_factory(TechMS(config=config))
        response = local_server.make_call(requests.get, '/env', timeout=500)
        assert response.status_code == 200
        assert response.text == "Simple microservice for test environment variable.\n"

    def test_run_example(self):
        app = CwsCLIFactory.import_attr('example', 'app', cwd=EXAMPLE_DIR)
        port = ThreadedLocalServer.unused_tcp_port()
        server = threading.Thread(target=run_server_example, args=(app, port), daemon=True)
        server.start()
        counter = 1
        time.sleep(counter)
        while not server.is_alive() and counter < 3:
            time.sleep(counter)
            counter += 1
        response = requests.get(f'http://localhost:{port}/')
        assert response.text == "Simple microservice for test.\n"
        response = requests.get(f'http://localhost:{port}/', params={"usage": "demo"})
        assert response.status_code == 200
        assert response.text == "Simple microservice for demo.\n"
        app.local_server.shutdown()


def run_server_example(app, port):
    print(f"Server starting on port {port}")
    app.run(host='localhost', port=port, project_dir=EXAMPLE_DIR)
