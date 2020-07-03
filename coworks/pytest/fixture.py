import json
import os
from pathlib import Path

import pytest

from .local_server import ThreadedLocalServer
from .. import TechMicroService
from ..config import DEFAULT_PROJECT_DIR, DEFAULT_WORKSPACE


@pytest.fixture()
def local_server_factory():
    threaded_server = ThreadedLocalServer()

    def create_server(app: TechMicroService, **kwargs):
        kwargs.setdefault('project_dir', DEFAULT_PROJECT_DIR)
        kwargs.setdefault('workspace', DEFAULT_WORKSPACE)
        app.deferred_init(**kwargs)

        # if config_path defined, use it to update environment from conf json file
        if app.config.environment_variables_file:
            var_file = Path(kwargs['project_dir']) / app.config.environment_variables_file
            try:
                with open(var_file) as f:
                    os.environ.update(json.loads(f.read()))
            except FileNotFoundError:
                workspace = app.config.workspace
                raise FileNotFoundError(f"Cannot find environment file {var_file} for workspace {workspace}.")
            except Exception:
                raise FileNotFoundError(f"No wrokspace defined in config.")

        threaded_server.configure(app, **kwargs)
        threaded_server.start()
        return threaded_server

    try:
        yield create_server
    finally:
        threaded_server.shutdown()
