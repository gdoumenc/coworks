import contextlib
import os
import socket
import sys
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest


def fixture_example_dir():
    return os.getenv('EXAMPLE_DIR', 'tests/cws/src')


def fixture_samples_docs_dir():
    return os.getenv('SAMPLES_DOCS_DIR', 'samples/docs/tech')


@pytest.fixture
def example_dir():
    yield fixture_example_dir()


@pytest.fixture
def samples_docs_dir():
    yield fixture_samples_docs_dir()


@pytest.fixture
def progressbar():
    yield MagicMock()


@pytest.fixture
def unused_tcp_port():
    with contextlib.closing(socket.socket()) as sock:
        sock.bind(('localhost', 0))
        return sock.getsockname()[1]


@pytest.fixture
def auth_headers():
    yield {
        'authorization': 'pytest',
    }


@pytest.fixture
def empty_context():
    return LambdaContextTest()


@contextmanager
def project_dir_context(project_dir):
    sys.path.insert(0, project_dir)
    try:
        yield
    finally:
        sys.path.remove(project_dir)


class LambdaContextTest:
    ...


def pytest_sessionstart():
    if not os.path.exists(fixture_samples_docs_dir()):
        msg = "Undefined samples folder: (environment variable 'SAMPLES_DOCS_DIR' must be redefined)."
        raise pytest.UsageError(msg)
    if not os.path.exists(fixture_example_dir()):
        msg = "Undefined example folder: (environment variable 'EXAMPLE_DIR' must be redefined)."
        raise pytest.UsageError(msg)
