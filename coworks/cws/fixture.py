import os

import pytest

from coworks import TechMicroService
from .runner import ThreadedLocalServer
from ..config import DEFAULT_PROJECT_DIR, DEFAULT_WORKSPACE


@pytest.fixture
def local_server_factory():
    threaded_server = ThreadedLocalServer()

    def create_server(app: TechMicroService, **kwargs):
        project_dir = kwargs.setdefault('project_dir', DEFAULT_PROJECT_DIR)
        workspace = kwargs.setdefault('workspace', DEFAULT_WORKSPACE)
        os.environ['WORKSPACE'] = workspace

        # if config_path defined, use it to update environment from conf json file
        config = app.get_config(workspace)
        config.load_environment_variables(project_dir)

        # chalice local server needs those variables in config not in command parameters
        setattr(config, 'function_name', 'api_handler')
        setattr(config, 'lambda_timeout', 100)
        setattr(config, 'lambda_memory_size', 100)

        app.deferred_init(workspace)
        threaded_server.configure(app, config)
        threaded_server.start()
        return threaded_server

    try:
        yield create_server
    finally:
        threaded_server.shutdown()
