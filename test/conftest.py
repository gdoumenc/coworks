import os
import pytest
import json

from chalice.config import Config

from .local_server import ThreadedLocalServer


@pytest.fixture()
def local_server_factory():
    threaded_server = ThreadedLocalServer()

    def create_server(app, **kwargs):

        # if config_path defined, use it to update environment from conf json file
        if 'config_path' in kwargs:
            config_path = kwargs.pop('config_path')
            config_file = os.path.join(config_path, '.chalice', 'config.json')
            with open(config_file) as f:
                config_from_disk = json.loads(f.read())
            config = Config(config_from_disk=config_from_disk)
            os.environ.update(config.environment_variables)
            kwargs['config'] = config

        threaded_server.configure(app, **kwargs)
        threaded_server.start()
        return threaded_server

    try:
        yield create_server
    finally:
        threaded_server.shutdown()
