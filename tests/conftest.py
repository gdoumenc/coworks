import contextlib
import os
import socket

import pytest


def fixture_example_dir():
    return os.getenv('EXAMPLE_DIR', 'tests/cws/src')


def fixture_samples_docs_dir():
    return os.getenv('SAMPLES_DOCS_DIR', 'samples/docs')


@pytest.fixture
def example_dir():
    yield fixture_example_dir()


@pytest.fixture
def samples_docs_dir():
    yield fixture_samples_docs_dir()


@pytest.fixture
def unused_tcp_port():
    with contextlib.closing(socket.socket()) as sock:
        sock.bind(('localhost', 0))
        return sock.getsockname()[1]


@pytest.fixture
def auth_headers():
    yield {
        'authorization': 'any',
    }


@pytest.fixture
def empty_context():
    return LambdaContextTest()


class LambdaContextTest:
    ...


def pytest_sessionstart():
    if not os.path.exists(fixture_samples_docs_dir()):
        msg = "Undefined samples folder: (environment variable 'SAMPLES_DOCS_DIR' must be redefined)."
        raise pytest.UsageError(msg)
    if not os.path.exists(fixture_example_dir()):
        msg = "Undefined example folder: (environment variable 'EXAMPLE_DIR' must be redefined)."
        raise pytest.UsageError(msg)
