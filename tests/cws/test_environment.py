import multiprocessing
import time
from pathlib import Path

import pytest
import requests
from flask.cli import ScriptInfo

from coworks.config import Config, ProdConfig
from coworks.cws.client import client
from tests.cws.src.app import EnvTechMS


class TestClass:
    def test_no_env(self, example_dir):
        with pytest.raises(AssertionError) as pytest_wrapped_e:
            app = EnvTechMS()
            with app.test_client() as c:
                response = c.get('/', headers={'Authorization': 'token'})
        assert pytest_wrapped_e.type == AssertionError
        assert pytest_wrapped_e.value.args[0] == "no environment variable 'test'"

    def test_run_dev_env(self, example_dir, unused_tcp_port):
        config = Config(environment_variables_file=Path("config") / "vars.dev.json")
        app = EnvTechMS(configs=config, root_path=example_dir)
        server = multiprocessing.Process(target=run_server, args=(example_dir, app, unused_tcp_port), daemon=True)
        server.start()
        counter = 1
        time.sleep(counter)
        while not server.is_alive() and counter < 3:
            time.sleep(counter)
            counter += 1
        response = requests.get(f'http://localhost:{unused_tcp_port}/env', headers={'Authorization': "token"})
        assert response.text == "Value of environment variable test is : test dev environment variable."
        server.terminate()

    def test_run_prod_env(self, example_dir, unused_tcp_port):
        config = Config(environment_variables_file=Path("config") / "vars.prod.json")
        app = EnvTechMS(configs=config, root_path=example_dir)
        server = multiprocessing.Process(target=run_server, args=(example_dir, app, unused_tcp_port), daemon=True)
        server.start()
        counter = 1
        time.sleep(counter)
        while not server.is_alive() and counter < 3:
            time.sleep(counter)
            counter += 1
        response = requests.get(f'http://localhost:{unused_tcp_port}/env', headers={'Authorization': "token"})
        assert response.text == "Value of environment variable test is : test prod environment variable."
        server.terminate()

    def test_run_dev_stage(self, example_dir, unused_tcp_port):
        config_dev = Config(environment_variables_file=Path("config") / "vars.dev.json")
        config_prod = ProdConfig(environment_variables_file=Path("config") / "vars.prod.json")
        app = EnvTechMS(configs=[config_dev, config_prod], root_path=example_dir)
        server = multiprocessing.Process(target=run_server_with_workspace,
                                         args=(example_dir, app, unused_tcp_port, "dev"),
                                         daemon=True)
        server.start()
        counter = 1
        time.sleep(counter)
        while not server.is_alive() and counter < 3:
            time.sleep(counter)
            counter += 1
        response = requests.get(f'http://localhost:{unused_tcp_port}/env', headers={'Authorization': "token"})
        assert response.text == "Value of environment variable test is : test dev environment variable."
        server.terminate()

    def test_run_prod_stage(self, example_dir, unused_tcp_port):
        config_dev = Config(environment_variables_file=Path("config") / "vars.dev.json")
        config_prod = ProdConfig(environment_variables_file=Path("config") / "vars.prod.json")
        app = EnvTechMS(configs=[config_dev, config_prod], root_path=example_dir)
        app.any_token_authorized = True
        server = multiprocessing.Process(target=run_server_with_workspace,
                                         args=(example_dir, app, unused_tcp_port, "v1"),
                                         daemon=True)
        server.start()
        counter = 1
        time.sleep(counter)
        while not server.is_alive() and counter < 3:
            time.sleep(counter)
            counter += 1
        response = requests.get(f'http://localhost:{unused_tcp_port}/env', headers={'Authorization': "token"})
        assert response.text == "Value of environment variable test is : test prod environment variable."
        server.terminate()

    def test_env_var(self, example_dir, unused_tcp_port):
        config = Config(environment_variables={'test': 'test value environment variable'})
        app = EnvTechMS(configs=config, root_path=example_dir)
        app.any_token_authorized = True
        server = multiprocessing.Process(target=run_server, args=(example_dir, app, unused_tcp_port), daemon=True)
        server.start()
        counter = 1
        time.sleep(counter)
        while not server.is_alive() and counter < 3:
            time.sleep(counter)
            counter += 1
        response = requests.get(f'http://localhost:{unused_tcp_port}/env', headers={'Authorization': "token"})
        assert response.text == "Value of environment variable test is : test value environment variable."
        server.terminate()


def run_server(project_dir, app, port):
    obj = ScriptInfo(create_app=lambda _: app, set_debug_flag=False)
    client.main(['--project-dir', project_dir, 'run', '--port', port], 'cws', obj=obj, standalone_mode=False)


def run_server_with_workspace(project_dir, app, port, workspace):
    obj = ScriptInfo(create_app=lambda _: app, set_debug_flag=False)
    client.main(['-p', project_dir, '-w', workspace, 'run', '--port', port], 'cws', obj=obj, standalone_mode=False)
