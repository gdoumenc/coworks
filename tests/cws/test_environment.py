import multiprocessing
import os
import time
from unittest import mock

import pytest
import requests
from flask.cli import ScriptInfo

from coworks.cws.client import client
from coworks.utils import load_dotenv
from tests.coworks.event import get_event
from tests.cws.src.app import EnvTechMS


@pytest.mark.not_on_github
class TestClass:

    @mock.patch.dict(os.environ, {"FLASK_ENV_FILE": ".env.no", "FLASK_RUN_FROM_CLI": "true"})
    def test_no_env(self, example_dir, empty_aws_context):
        app = EnvTechMS()
        event = get_event('/', 'get')
        with app.cws_client(event, empty_aws_context) as c:
            response = c.get('/', headers={'Authorization': 'token'})

    @mock.patch.dict(os.environ, {"FLASK_ENV_FILE": '.env.dev', "FLASK_RUN_FROM_CLI": "true"})
    def test_run_dev_env(self, example_dir, unused_tcp_port):
        server = multiprocessing.Process(target=run_server, args=(example_dir, unused_tcp_port), daemon=True)
        server.start()
        counter = 1
        time.sleep(counter)
        while not server.is_alive() and counter < 3:
            time.sleep(counter)
            counter += 1
        response = requests.get(f'http://localhost:{unused_tcp_port}/env', headers={'Authorization': "token"})
        assert response.text == "Value of environment variable test is : test dev environment variable."
        server.terminate()

    @mock.patch.dict(os.environ, {"FLASK_ENV_FILE": '.env.v1', "FLASK_RUN_FROM_CLI": "true"})
    def test_run_prod_env(self, example_dir, unused_tcp_port):
        server = multiprocessing.Process(target=run_server, args=(example_dir, unused_tcp_port), daemon=True)
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
        server = multiprocessing.Process(target=run_server_with_stage,
                                         args=(example_dir, unused_tcp_port, "dev"),
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
        server = multiprocessing.Process(target=run_server_with_stage,
                                         args=(example_dir, unused_tcp_port, "v1"),
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

    import pytest
    @pytest.mark.wip
    def test_load_env(self):
        variables = load_dotenv("dev")
        assert True


def run_server(project_dir, port):
    obj = ScriptInfo(create_app=lambda: EnvTechMS(), set_debug_flag=False)
    client.main(['--project-dir', '.', 'run', '--port', port], 'cws', obj=obj, standalone_mode=False)


def run_server_with_stage(project_dir, port, stage):
    @mock.patch.dict(os.environ, {"FLASK_ENV_FILE": f".env.{stage}", "FLASK_RUN_FROM_CLI": "true"})
    def run():
        obj = ScriptInfo(create_app=lambda: EnvTechMS(), set_debug_flag=False)
        client.main(['-p', '.', 'run', '--port', port], 'cws', obj=obj, standalone_mode=False)

    run()
