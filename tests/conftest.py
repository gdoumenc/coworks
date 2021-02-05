from aws_xray_sdk import core as xray_core

from tests.fixture import *


def pytest_sessionstart():
    samples_dir = os.getenv("SAMPLES_DOCS_DIR")
    if not os.path.exists(samples_dir):
        raise pytest.UsageError(f"Undefined samples folder: {samples_dir} (value defined in pytest.ini).")
    example_dir = os.getenv("EXAMPLE_DIR")
    if not os.path.exists(example_dir):
        raise pytest.UsageError(f"Undefined example folder: {example_dir} (value defined in pytest.ini).")

    # mock aws
    xray_core.recorder.capture = lambda _: lambda y: y
    xray_core.recorder.current_subsegment = lambda: MagicMock()
