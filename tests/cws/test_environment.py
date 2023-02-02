import multiprocessing
import os
import time
from unittest import mock

import pytest
import requests
from flask.cli import ScriptInfo

from coworks.cws.client import client
from tests.coworks.event import get_event
from tests.cws.src.app import EnvTechMS


class TestClass:

    @mock.patch.dict(os.environ, {"CWS_STAGE": "no", "FLASK_RUN_FROM_CLI": "true"})
    def test_no_env(self, example_dir, empty_aws_context):
        os.environ.pop("STAGE")
        with pytest.raises(AssertionError) as pytest_wrapped_e:
            app = EnvTechMS()
            event = get_event('/', 'get')
            with app.cws_client(event, empty_aws_context) as c:
                response = c.get('/', headers={'Authorization': 'token'})
        assert pytest_wrapped_e.type == AssertionError
        assert pytest_wrapped_e.value.args[0] == "no environment variable 'STAGE'"

    @mock.patch.dict(os.environ, {"CWS_STAGE": 'dev', "FLASK_RUN_FROM_CLI": "true"})
    def test_run_dev_env(self, example_dir, unused_tcp_port):
        os.environ.pop('TEST', None)
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

    @mock.patch.dict(os.environ, {"CWS_STAGE": 'v1', "FLASK_RUN_FROM_CLI": "true"})
    def test_run_prod_env(self, example_dir, unused_tcp_port):
        os.environ.pop('TEST', None)
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
        os.environ.pop('TEST', None)
        server = multiprocessing.Process(target=run_server_with_workspace,
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
        os.environ.pop('TEST', None)
        server = multiprocessing.Process(target=run_server_with_workspace,
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


def run_server(project_dir, port):
    obj = ScriptInfo(create_app=lambda: EnvTechMS(), set_debug_flag=False)
    client.main(['--project-dir', '.', 'run', '--port', port], 'cws', obj=obj, standalone_mode=False)


def run_server_with_workspace(project_dir, port, workspace):
    @mock.patch.dict(os.environ, {"CWS_STAGE": workspace, "FLASK_RUN_FROM_CLI": "true"})
    def run():
        obj = ScriptInfo(create_app=lambda: EnvTechMS(), set_debug_flag=False)
        client.main(['-p', '.', 'run', '--port', port], 'cws', obj=obj, standalone_mode=False)

    run()
