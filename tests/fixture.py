import os
import pytest
from unittest.mock import MagicMock

from coworks import TechMicroService
from coworks.config import DEFAULT_PROJECT_DIR, DEFAULT_WORKSPACE
from coworks.cws.runner import ThreadedLocalServer
from tests.mockup import email_mock, smtp_mock


@pytest.fixture
def example_dir():
    return os.getenv('EXAMPLE_DIR')


@pytest.fixture
def samples_docs_dir():
    return os.getenv('SAMPLES_DOCS_DIR')


@pytest.fixture
def email_mock_fixture():
    yield email_mock


@pytest.fixture
def smtp_mock_fixture():
    yield smtp_mock


s3session_mock = MagicMock()


@pytest.fixture
def s3_session():
    class S3Session:
        mock = s3session_mock

        def __new__(cls, *args, **kwargs):
            return s3session_mock

    yield S3Session


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
