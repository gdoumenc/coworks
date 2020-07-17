import os

import pytest

from coworks import TechMicroService
from .runner import ThreadedLocalServer
from ..config import DEFAULT_PROJECT_DIR, DEFAULT_WORKSPACE


@pytest.fixture
def local_server_factory():
    threaded_server = ThreadedLocalServer()

    def create_server(app: TechMicroService, **kwargs):
        kwargs.setdefault('project_dir', DEFAULT_PROJECT_DIR)
        kwargs.setdefault('workspace', DEFAULT_WORKSPACE)

        # if config_path defined, use it to update environment from conf json file
        os.environ['WORKSPACE'] = kwargs['workspace']
        app.deferred_init(kwargs['workspace'])
        app.config.load_environment_variables(kwargs['project_dir'])

        threaded_server.configure(app, **kwargs)
        threaded_server.start()
        return threaded_server

    try:
        yield create_server
    finally:
        threaded_server.shutdown()
