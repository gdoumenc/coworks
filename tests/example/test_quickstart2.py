import io
import threading
import time

import requests

from coworks.utils import import_attr
from coworks.pytest.local_server import ThreadedLocalServer


class TestClass:

    def test_run_quickstart(self, example_dir):
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
        app.local_server.shutdown()

    def test_export_quickstart(self, example_dir):
        app = import_attr('quickstart2', 'app', cwd=example_dir)
        output = io.StringIO()
        app.commands['export'].execute(output, project_dir=example_dir)
        output.seek(0)
        print(output.read())


def run_server_quickstart(app, port, example_dir):
    print(f"Server starting on port {port}")
    app.commands['run'].execute(host='localhost', port=port, project_dir=example_dir)
