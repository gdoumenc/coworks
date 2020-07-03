import io
import threading
import time
from pathlib import Path

import requests

from coworks.config import Config
from coworks.utils import import_attr
from coworks.pytest.local_server import ThreadedLocalServer
from .example import TechMS


class TestClass:

    def test_env(self, local_server_factory, example_dir):
        config = Config(environment_variables_file=Path(example_dir) / "config" / "vars_prod.secret.json")
        local_server = local_server_factory(TechMS(configs=[config]))
        response = local_server.make_call(requests.get, '/env', timeout=500)
        assert response.status_code == 200
        assert response.text == "Simple microservice for test prod environment variable.\n"

    def test_run_quickstart(self, example_dir):
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
        assert response.text == "Simple microservice ready.\n"
        app.local_server.shutdown()

    def test_export_quickstart(self, example_dir):
        app = import_attr('quickstart3', 'app', cwd=example_dir)
        output = io.StringIO()
        app.commands['export'].execute(module='quickstart3', service='app', output=output, project_dir=example_dir,
                                       workspace='dev', step='update', config=None)
        output.seek(0)
        print(output.read())


def run_server_quickstart(app, port, example_dir):
    print(f"Server starting on port {port}")
    app.commands['run'].execute(host='localhost', port=port, project_dir=example_dir)
