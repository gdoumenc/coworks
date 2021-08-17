import os
import threading
import time
from pathlib import Path

import pytest
import requests

from coworks.config import Config, ProdConfig
from coworks.cws.runner import CwsRunner
from coworks.cws.runner import ThreadedLocalServer
from tests.coworks.ms import *


class WithEnvMS(SimpleMS):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        @self.before_first_activation
        def init(event, context):
            assert os.getenv("test") is not None

    @entry
    def get(self):
        """Root access."""
        return os.getenv("test")


import pytest
@pytest.mark.skip
class TestClass:

    def test_dev_stage(self, local_server_factory, example_dir):
        config = Config(environment_variables_file=Path(example_dir) / "config" / "vars_dev.json")
        local_server = local_server_factory(WithEnvMS(configs=config))
        response = local_server.make_call(requests.get, '/')
        assert response.status_code == 200
        assert response.text == 'test dev environment variable'

    def test_run_dev_stage(self, example_dir):
        config = Config(environment_variables_file=Path("config") / "vars_dev.json")
        app = WithEnvMS(configs=config)
        CwsRunner(app)
        port = ThreadedLocalServer.unused_tcp_port()
        server = threading.Thread(target=run_server_example, args=(example_dir, app, port), daemon=True)
        server.start()
        counter = 1
        time.sleep(counter)
        while not server.is_alive() and counter < 3:
            time.sleep(counter)
            counter += 1
        response = requests.get(f'http://localhost:{port}/', headers={'Authorization': "token"})
        assert response.text == "test dev environment variable"

    def test_secret_stage(self, local_server_factory, example_dir):
        config = Config(environment_variables_file=Path(example_dir) / "config" / "vars_prod.json")
        local_server = local_server_factory(WithEnvMS(configs=config))
        response = local_server.make_call(requests.get, '/')
        assert response.status_code == 200
        assert response.text == 'test secret environment variable'

    def test_workspace_stage(self, local_server_factory, example_dir):
        config = Config(workspace='test', environment_variables_file=Path(example_dir) / "config" / "vars_prod.json")
        local_server = local_server_factory(WithEnvMS(configs=config), workspace='test')
        response = local_server.make_call(requests.get, '/')
        assert response.status_code == 200
        assert response.text == 'test secret environment variable'

    def test_prod_stage(self, local_server_factory, example_dir):
        def auth(*args):
            return True

        config1 = Config(environment_variables_file=Path(example_dir) / "config" / "vars_dev.json")
        config2 = ProdConfig(environment_variables_file=Path(example_dir) / "config" / "vars_prod.json", auth=auth)
        local_server = local_server_factory(WithEnvMS(configs=[config1, config2]), workspace="v1")
        response = local_server.make_call(requests.get, '/', headers={'authorization':'token'})
        assert response.status_code == 200
        assert response.text == 'test secret environment variable'

    def test_not_prod_stage(self, local_server_factory, example_dir):
        config1 = Config(workspace='1', environment_variables_file=Path(example_dir) / "config" / "vars_dev.json")
        config2 = ProdConfig(environment_variables_file=Path(example_dir) / "config" / "vars_prod.json")
        local_server = local_server_factory(WithEnvMS(configs=[config1, config2]), workspace='1')
        response = local_server.make_call(requests.get, '/')
        assert response.status_code == 200
        assert response.text == 'test dev environment variable'

    def test_no_config_stage(self, local_server_factory, example_dir):
        config1 = Config(environment_variables_file=Path(example_dir) / "config" / "vars_dev.json")
        config2 = ProdConfig(environment_variables_file=Path(example_dir) / "config" / "vars_prod.json")
        local_server = local_server_factory(WithEnvMS(configs=[config1, config2]),
                                            project_dir=Path(example_dir) / "config", workspace='1')
        response = local_server.make_call(requests.get, '/')
        assert response.status_code == 200
        assert response.text == 'test default environment variable'

    def test_env_var(self, local_server_factory):
        config = Config(environment_variables={'test': 'test value environment variable'})
        local_server = local_server_factory(WithEnvMS(configs=config))
        response = local_server.make_call(requests.get, '/')
        assert response.status_code == 200
        assert response.text == 'test value environment variable'

    def test_wrong_env_var_name(self, local_server_factory):
        config = Config(environment_variables={'1test': 'test value environment variable'})
        with pytest.raises(KeyError) as pytest_wrapped_e:
            local_server = local_server_factory(WithEnvMS(configs=config))
        assert pytest_wrapped_e.type == KeyError
        assert pytest_wrapped_e.value.args[0] == "Wrong environment variable name: 1test"


def run_server_example(example_dir, app, port):
    print(f"Server starting on port {port}")
    app.execute('run', host='localhost', port=port, project_dir=example_dir, module='example', workspace='dev')
