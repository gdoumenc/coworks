import os
import threading
import time

import requests

from coworks.cws.client import CwsCLIFactory
from coworks.pytest.local_server import ThreadedLocalServer
from .example import TechMS

EXAMPLE_DIR = os.getenv('EXAMPLE_DIR')


def test_simple_example(local_server_factory):
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


def test_params(local_server_factory):
    local_server = local_server_factory(TechMS())
    response = local_server.make_call(requests.put, '/value/1', json=456)
    assert response.status_code == 200
    assert response.text == "456"
    response = local_server.make_call(requests.get, '/value/1')
    assert response.status_code == 200
    assert response.text == "456\n"


def test_env(local_server_factory):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    local_server = local_server_factory(TechMS(), config_path=dir_path)
    response = local_server.make_call(requests.get, '/env')
    assert response.status_code == 200
    assert response.text == "Simple microservice for test environment variable.\n"


def run_server_example(app, port):
    print(f"Server starting on port {port}")
    app.run(host='localhost', port=port, project_dir=EXAMPLE_DIR)


def test_run_example():
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
