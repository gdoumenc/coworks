import os
from unittest.mock import Mock, MagicMock

import pytest

from coworks.cws.fixture import local_server_factory as factory
from tests.mockup import email_mock, smtp_mock, boto3_mock


@pytest.fixture
def example_dir():
    return os.getenv('EXAMPLE_DIR')


@pytest.fixture
def zipfile_mock(request):
    import zipfile

    file = MagicMock()
    file.__enter__ = Mock(return_value=file)
    file.write = Mock()
    zip_mock = Mock(return_value=file)
    zip_mock.file = file

    save_zip_file = zipfile.ZipFile
    zipfile.ZipFile = zip_mock

    def end():
        zipfile.ZipFile = save_zip_file

    request.addfinalizer(end)
    return zip_mock


@pytest.fixture
def email_mock_fixture():
    yield email_mock


@pytest.fixture
def smtp_mock_fixture():
    yield smtp_mock


@pytest.fixture
def boto3_mock_fixture():
    yield boto3_mock


local_server_factory = factory


def pytest_sessionstart():
    example_dir = os.getenv('EXAMPLE_DIR')
    if not os.path.exists(example_dir):
        raise pytest.UsageError(f"Undefined example folder: {example_dir} (value defined in pytest.ini).")
