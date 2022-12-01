import contextlib
import os
import socket
from unittest.mock import MagicMock

import pytest

from cws.client import CwsContext


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


def project_dir_context(project_dir):
    ctx = CwsContext(command=None, allow_extra_args={}, allow_interspersed_args={}, ignore_unknown_options={})
    ctx.add_project_dir(project_dir)
    return ctx


class LambdaContextTest:
    ...


def pytest_sessionstart():
    if not os.path.exists(fixture_samples_docs_dir()):
        msg = "Undefined samples folder: (environment variable 'SAMPLES_DOCS_DIR' must be redefined)."
        raise pytest.UsageError(msg)
    if not os.path.exists(fixture_example_dir()):
        msg = "Undefined example folder: (environment variable 'EXAMPLE_DIR' must be redefined)."
        raise pytest.UsageError(msg)
