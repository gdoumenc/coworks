# import pytest
# import requests
# import threading
# import time
# from pathlib import Path
#
# from coworks.config import Config, LocalConfig
# from coworks.cws.client import client
# from coworks.cws.runner import ThreadedLocalServer
# from coworks.utils import import_attr
# from tests.src.example import TechMS
#
#
# class TestClass:
#
#     def test_simple_example(self, local_server_factory):
#         local_server = local_server_factory(TechMS(configs=LocalConfig()))
#         response = local_server.make_call(requests.get, '/', timeout=500)
#         assert response.status_code == 200
#         assert response.text == "Simple microservice for test.\n"
#         response = local_server.make_call(requests.get, '/', params={"usage": "demo"})
#         assert response.status_code == 200
#         assert response.text == "Simple microservice for demo.\n"
#         response = local_server.make_call(requests.get, '/value/1')
#         assert response.status_code == 200
#         assert response.text == "0\n"
#         response = local_server.make_call(requests.put, '/value/1', json={"value": 456})
#         assert response.status_code == 200
#         assert response.text == "456"
#         response = local_server.make_call(requests.get, '/value/1')
#         assert response.status_code == 200
#         assert response.text == "456\n"
#
#     def test_params(self, local_server_factory):
#         local_server = local_server_factory(TechMS(configs=LocalConfig()))
#         response = local_server.make_call(requests.put, '/value/1', json=456)
#         assert response.status_code == 200
#         assert response.text == "456"
#         response = local_server.make_call(requests.get, '/value/1')
#         assert response.status_code == 200
#         assert response.text == "456\n"
#
#     def test_env(self, local_server_factory, example_dir):
#         config = Config(environment_variables_file=Path(example_dir) / "config" / "vars_dev.json")
#         local_server = local_server_factory(TechMS(configs=[config]))
#         response = local_server.make_call(requests.get, '/env', timeout=500)
#         assert response.status_code == 200
#         assert response.text == "Simple microservice for test dev environment variable.\n"
#
#     def test_init(self, local_server_factory, example_dir):
#         local_server = local_server_factory(TechMS(configs=[LocalConfig()]))
#         response = local_server.make_call(requests.get, '/init', timeout=500)
#         assert response.status_code == 200
#         assert response.text == "Initial value is test.\n"
#
#     def test_run_example(self, example_dir):
#         app = import_attr('example', 'app', cwd=example_dir)
#         port = ThreadedLocalServer.unused_tcp_port()
#         server = threading.Thread(target=run_server_example, args=(app, port, example_dir), daemon=True)
#         server.start()
#         counter = 1
#         time.sleep(counter)
#         while not server.is_alive() and counter < 3:
#             time.sleep(counter)
#             counter += 1
#         response = requests.get(f'http://localhost:{port}/')
#         assert response.text == "Simple microservice for test.\n"
#         response = requests.get(f'http://localhost:{port}/', params={"usage": "demo"})
#         assert response.status_code == 200
#         assert response.text == "Simple microservice for demo.\n"
#
#     def test_cmd_wrong_project_dir(self, example_dir, capsys):
#         with pytest.raises(SystemExit) as pytest_wrapped_e:
#             client(prog_name='cws', args=['-p', example_dir, 'inspect'], obj={})
#         assert pytest_wrapped_e.type == SystemExit
#         assert pytest_wrapped_e.value.code == 0
#         captured = capsys.readouterr()
#         assert captured.out == \
#                'Microservice project1 defined in module example\nMicroservice project2 defined in module example\n'
#
#
# def run_server_example(app, port, example_dir):
#     print(f"Server starting on port {port}")
#     app.execute('run', project_dir=example_dir, module='example', workspace='dev', host='localhost', port=port, )
