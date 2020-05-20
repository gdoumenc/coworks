import io
import os
import threading
import time

import requests

from coworks.cws.client import CwsCLIFactory, export_to_file
from coworks.pytest.local_server import ThreadedLocalServer

EXAMPLE_DIR = os.getenv('EXAMPLE_DIR')


def run_server_quickstart(app, port):
    print(f"Server starting on port {port}")
    app.run(host='localhost', port=port, project_dir=EXAMPLE_DIR)


def test_run_quickstart():
    app = CwsCLIFactory.import_attr('quickstart2', 'app', cwd=EXAMPLE_DIR)
    port = ThreadedLocalServer.unused_tcp_port()
    server = threading.Thread(target=run_server_quickstart, args=(app, port), daemon=True)
    server.start()
    counter = 1
    time.sleep(counter)
    while not server.is_alive() and counter < 3:
        time.sleep(counter)
        counter += 1
    response = requests.get(f'http://localhost:{port}/', headers={'Authorization': "token"})
    assert response.text == "Simple microservice ready.\n"
    app.local_server.shutdown()


def test_export_quickstart():
    app = CwsCLIFactory.import_attr('quickstart2', 'app', cwd=EXAMPLE_DIR)
    output = io.StringIO()
    export_to_file('quickstart2', 'app', 'terraform', output, project_dir=EXAMPLE_DIR)
    output.seek(0)
    print(output.read())
