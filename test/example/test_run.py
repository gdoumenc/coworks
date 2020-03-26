import threading

import pytest
import requests
import time
from coworks.cli import CWSFactory
from coworks.pytest.local_server import ThreadedLocalServer


def run_server(port):
    print(f"Server starting on port {port}")
    app = CWSFactory.import_attr('example', 'app', project_dir="test/example/")
    app.run(host='localhost', port=port, project_dir="test/example/")


def test_run_example():
    port = ThreadedLocalServer.unused_tcp_port()
    server = threading.Thread(target=run_server, args=(port,), daemon=True)
    server.start()
    time.sleep(2)
    response = requests.get(f'http://localhost:{port}/', timeout=100)
    assert response.text == "Simple microservice for test.\n"
    response = requests.get(f'http://localhost:{port}/', params={"usage": "demo"})
    assert response.status_code == 200
    assert response.text == "Simple microservice for demo.\n"
