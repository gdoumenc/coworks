import contextlib
import os
import socket
from unittest.mock import MagicMock

import pytest

fixture_example_dir = os.getenv('EXAMPLE_DIR', 'tests/cws/src')
fixture_samples_docs_dir = os.getenv('SAMPLES_DOCS_DIR', 'samples/docs')


@pytest.fixture
def example_dir(monkeypatch):
    monkeypatch.syspath_prepend(fixture_example_dir)
    monkeypatch.chdir(fixture_example_dir)
    yield fixture_example_dir


@pytest.fixture
def samples_docs_dir(monkeypatch):
    monkeypatch.syspath_prepend(fixture_example_dir)
    monkeypatch.chdir(fixture_samples_docs_dir)
    yield fixture_samples_docs_dir


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
def empty_aws_context():
    return object()


def pytest_sessionstart():
    if not os.path.exists(fixture_samples_docs_dir):
        msg = "Undefined samples folder: (environment variable 'SAMPLES_DOCS_DIR' must be redefined)."
        raise pytest.UsageError(msg)
    if not os.path.exists(fixture_example_dir):
        msg = "Undefined example folder: (environment variable 'EXAMPLE_DIR' must be redefined)."
        raise pytest.UsageError(msg)
