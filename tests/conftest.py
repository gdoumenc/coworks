import os
from unittest.mock import MagicMock

import pytest
from aws_xray_sdk import core as xray_core


def fixture_example_dir():
    return os.getenv('EXAMPLE_DIR')


def fixture_samples_docs_dir():
    return os.getenv('SAMPLES_DOCS_DIR')


@pytest.fixture
def example_dir():
    yield fixture_example_dir()


@pytest.fixture
def samples_docs_dir():
    yield fixture_samples_docs_dir()


def pytest_sessionstart():
    if not os.path.exists(fixture_samples_docs_dir()):
        msg = "Undefined samples folder: (var defined in pytest.ini)."
        raise pytest.UsageError(msg)
    if not os.path.exists(fixture_example_dir()):
        msg = "Undefined example folder: (var defined in pytest.ini)."
        raise pytest.UsageError(msg)

    # mock aws xray
    xray_core.recorder.capture = lambda _: lambda y: y
    xray_core.recorder.current_subsegment = lambda: MagicMock()
