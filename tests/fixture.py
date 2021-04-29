from unittest.mock import MagicMock

from coworks.fixture import *
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
