import os
import threading
import time
from pathlib import Path

import requests

from coworks.config import Config
from coworks.cws.runner import CwsRunner
from coworks.cws.runner import ThreadedLocalServer
from tests.src.coworks.tech_ms import *

EXAMPLE_DIR = os.getenv('EXAMPLE_DIR')


class WithEnvMS(SimpleMS):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        @self.before_first_activation
        def init(event, context):
            assert os.getenv("test") is not None

    def get(self):
        """Root access."""
        return os.getenv("test")


class TestClass:

    def test_dev_stage(self, local_server_factory):
        config = Config(environment_variables_file=Path(EXAMPLE_DIR) / "config" / "vars_dev.json")
        local_server = local_server_factory(WithEnvMS(configs=config))
        response = local_server.make_call(requests.get, '/')
        assert response.status_code == 200
        assert response.text == 'test dev environment variable'

    def test_run_dev_stage(self, example_dir):
        config = Config(environment_variables_file=Path(EXAMPLE_DIR) / "config" / "vars_dev.json")
        app = WithEnvMS(configs=config)
        CwsRunner(app)
        port = ThreadedLocalServer.unused_tcp_port()
        server = threading.Thread(target=run_server_example, args=(app, port), daemon=True)
        server.start()
        counter = 1
        time.sleep(counter)
        while not server.is_alive() and counter < 3:
            time.sleep(counter)
            counter += 1
        response = requests.get(f'http://localhost:{port}/', headers={'Authorization': "token"})
        assert response.text == "test dev environment variable"

    def test_prod_stage(self, local_server_factory):
        config = Config(environment_variables_file=Path(EXAMPLE_DIR) / "config" / "vars_prod.json")
        local_server = local_server_factory(WithEnvMS(configs=config))
        response = local_server.make_call(requests.get, '/')
        assert response.status_code == 200
        assert response.text == 'test prod environment variable'

    def test_env_var(self, local_server_factory):
        config = Config(environment_variables={'test': 'test value environment variable'})
        local_server = local_server_factory(WithEnvMS(configs=config))
        response = local_server.make_call(requests.get, '/')
        assert response.status_code == 200
        assert response.text == 'test value environment variable'


def run_server_example(app, port):
    print(f"Server starting on port {port}")
    app.execute('run', host='localhost', port=port, project_dir='.', module='example', workspace='dev')
