import json
import os

import pytest
from chalice.config import Config
from chalice.cli import DEFAULT_STAGE_NAME

from .local_server import ThreadedLocalServer


@pytest.fixture()
def local_server_factory():
    threaded_server = ThreadedLocalServer()

    def create_server(app, **kwargs):

        # if config_path defined, use it to update environment from conf json file
        if app.config.environment_variables_file:
            with open(app.config.environment_variables_file) as f:
                os.environ.update(json.loads(f.read()))

        threaded_server.configure(app, **kwargs)
        threaded_server.start()
        return threaded_server

    try:
        yield create_server
    finally:
        threaded_server.shutdown()
