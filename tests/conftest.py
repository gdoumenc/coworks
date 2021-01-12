import os
from unittest.mock import MagicMock

import pytest
from aws_xray_sdk import core as xray_core

from tests.fixture import local_server_factory as factory
from tests.mockup import email_mock, smtp_mock


@pytest.fixture
def example_dir():
    return os.getenv('EXAMPLE_DIR')


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


local_server_factory = factory


def pytest_sessionstart():
    example_dir = os.getenv('EXAMPLE_DIR')
    if not os.path.exists(example_dir):
        raise pytest.UsageError(f"Undefined example folder: {example_dir} (value defined in pytest.ini).")

    # mock aws
    xray_core.recorder.capture = lambda _: lambda y: y
    xray_core.recorder.current_subsegment = lambda: MagicMock()
