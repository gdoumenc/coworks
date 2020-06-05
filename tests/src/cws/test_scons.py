import os
import sys
from dataclasses import dataclass


@dataclass
class Target:
    name: str


class TestClass:
    def test_zip(self, monkeypatch, zipfile_mock, example_dir):
        # hack for strange installation of scons
        for path in [f"{p}/scons" for p in sys.path if 'site-package' in p]:
            monkeypatch.syspath_prepend(path)
        from coworks.cws.layers import generate_zip_file
        env = {
            'SRC_DIRS': [example_dir],
            'MODULES': ["chalice", "aws_xray_sdk"],
            'EXCLUDE_DIRS': [os.path.join(example_dir, 'config')],
            'EXCLUDE_FILE_PATTERN': "Pipfile",
        }

        generate_zip_file([Target("test")], None, env=env)
        zipfile_mock.assert_called_with("test", mode='w')

        filename_args = ([c[1][1].as_posix() for c in zipfile_mock.file.write.mock_calls])
        assert 'python/chalice/app.py' in filename_args
        assert 'python/tests/example/quickstart2.py' in filename_args
        assert 'python/tests/example/config/vars_dev.json' not in filename_args
        assert 'python/tests/example/Pipfile' not in filename_args
