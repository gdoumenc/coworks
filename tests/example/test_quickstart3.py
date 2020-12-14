import io
import threading
import time

import requests

from coworks.cws.runner import ThreadedLocalServer
from coworks.utils import import_attr


class TestClass:

    def test_run_quickstart3(self, example_dir):
        app = import_attr('quickstart3', 'app', cwd=example_dir)
        port = ThreadedLocalServer.unused_tcp_port()
        server = threading.Thread(target=run_server_quickstart, args=(app, port, example_dir), daemon=True)
        server.start()
        counter = 1
        time.sleep(counter)
        while not server.is_alive() and counter < 3:
            time.sleep(counter)
            counter += 1
        response = requests.get(f'http://localhost:{port}/', headers={'Authorization': "token"})
        assert response.text == "Stored value 0.\n"
        response = requests.post(f'http://localhost:{port}/', params={'value':1}, headers={'Authorization': "token"})
        assert response.text == "Value stored.\n"
        response = requests.get(f'http://localhost:{port}/', headers={'Authorization': "token"})
        assert response.text == "Stored value 1.\n"

    def test_export_quickstart3(self, example_dir):
        app = import_attr('quickstart3', 'app', cwd=example_dir)
        output = io.StringIO()
        app.execute('export', project_dir=example_dir, module='quickstart3', workspace='dev', output=output)
        output.seek(0)
        print(output.read())


def run_server_quickstart(app, port, example_dir):
    print(f"Server starting on port {port}")
    app.execute('run', host='localhost', port=port, project_dir=example_dir, module='quickstart3', workspace='dev')
