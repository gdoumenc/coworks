import os
import sys
from unittest import mock

import pytest

from coworks.cws.client import client


class TestClass:
    @mock.patch.dict(os.environ, {"FLASK_APP": "cmd:app"})
    def test_no_project_file_no_module(self, example_dir, capsys):
        assert example_dir not in sys.path
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['--project-dir', example_dir, 'test'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
        assert example_dir not in sys.path
