import pytest
import os

from coworks.pytest.fixture import local_server_factory as factory
from tests.mockup import email_mock, smtp_mock, boto3_mock


@pytest.fixture()
def email_mock_fixture():
    yield email_mock


@pytest.fixture()
def smtp_mock_fixture():
    yield smtp_mock


@pytest.fixture()
def boto3_mock_fixture():
    yield boto3_mock


local_server_factory = factory


def pytest_sessionstart():
    example_dir = os.getenv('EXAMPLE_DIR')
    if not os.path.exists(example_dir):
        raise pytest.UsageError("Undefined example folder: {example_dir}.")

