import pytest

from test.mockup import email_mock, smtp_mock, boto3_mock
from coworks.pytest.fixture import local_server_factory as factory


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
