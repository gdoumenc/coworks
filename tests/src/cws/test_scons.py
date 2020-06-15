import os
import sys
from dataclasses import dataclass


class Dir:
    def __init__(self, dir):
        self.dir = dir

    def get_abspath(self):
        return os.path.join(os.getcwd(), self.dir)


@dataclass
class Target:
    dir: Dir
    name: str


class TestClass:
    def test_zip(self, monkeypatch, zipfile_mock, example_dir):
        # hack for strange installation of scons
        for path in [f"{p}/scons" for p in sys.path if 'site-package' in p]:
            monkeypatch.syspath_prepend(path)
        from coworks.cws.layers import Layer

        env = {
            'modules': ["chalice", "aws_xray_sdk"],
            'source_dirs': [example_dir],
            'exclude_dirs': [os.path.join(example_dir, 'config')],
            'exclude_file_pattern': r"(Pipfile)|(.*\.tf)|(.*\.http)",
        }
        layer = Layer('test', **env)
        layer.generate_zip_file([Target(Dir('test'), 'test')], None)
        zipfile_mock.assert_called_with(os.path.join(os.getcwd(), 'test', 'test'), mode='w')

        filename_args = ([c[1][1].as_posix() for c in zipfile_mock.file.write.mock_calls])
        assert 'python/chalice/app.py' in filename_args
        assert 'python/quickstart2.py' in filename_args
        assert 'python/config/vars_dev.json' not in filename_args
        assert 'python/Pipfile' not in filename_args
        assert 'python/quickstart2.tf' not in filename_args
        assert 'python/request.http' not in filename_args
