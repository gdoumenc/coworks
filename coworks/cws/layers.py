import importlib.util
import os
import re
from functools import partial
from pathlib import Path
from typing import Optional, Iterable
from zipfile import ZipFile

from SCons import Environment
from SCons.Builder import Builder

DEFAULT_MODULES = [
    'coworks',
    'chalice', 'aws_xray_sdk', 'jsonpickle', 'wrapt',
    'jinja2', 'yaml', 'markupsafe',
    'requests', 'chardet', 'certifi', 'idna', 'requests_toolbelt', 'zeep',
]
EXCLUDE_FILE_PATTERN = r".*.py[co]"


class Layer:

    def __init__(self, layer_zipfilename: str, modules: Optional[Iterable] = None,
                 source_dirs: Optional[Iterable] = None,
                 exclude_dirs: Optional[Iterable] = None, exclude_file_pattern: str = None):
        """
        Create a zip file for AWS Layer.
        :param layer_zipfilename: zip file name.
        :param modules: list of python modules to include from current virtual env.
        :param source_dirs: list of source directories to include.
        :param exclude_dirs: list of source directories to exclude.
        :param exclude_file_pattern: regular pattern file to exclude.
        :return: None.
        """
        self.__source_dirs = source_dirs or []
        self.__modules = modules if modules is not None else DEFAULT_MODULES
        self.__exclude_dirs = exclude_dirs or []
        self.__exclude_file_pattern = exclude_file_pattern
        self.__exclude_regexp = None

        env = Environment.Base(BUILDERS={'Layer': Builder(action=partial(self.generate_zip_file, target=self))})

        def add_dep(_, root, file):
            dependencies.append(Path(root) / file)

        dependencies = []
        for source_dir in self.__source_dirs:
            self.walk(add_dep, source_dir)
        for module in self.__modules:
            spec = importlib.util.find_spec(module)
            if spec:
                if spec.submodule_search_locations:
                    for location in spec.submodule_search_locations:
                        self.walk(add_dep, location)
        env.Layer(layer_zipfilename, [file.as_posix() for file in dependencies])

    @property
    def exclude_regexp(self):
        if not self.__exclude_regexp:
            if self.__exclude_file_pattern:
                self.__exclude_regexp = re.compile(rf'{EXCLUDE_FILE_PATTERN}|{self.__exclude_file_pattern}')
            else:
                self.__exclude_regexp = re.compile(EXCLUDE_FILE_PATTERN)
        return self.__exclude_regexp

    def generate_zip_file(self, target, source, env=None):
        for t in target:
            zip_path = os.path.join(t.dir.get_abspath(), t.name)
            with ZipFile(zip_path, mode='w') as layer_zip:
                def add_zip(root, parent, file, zip_prefix=None):
                    dirs = Path(parent).relative_to(root)
                    layer_zip.write(Path(parent) / file, zip_prefix / dirs / file)

                for source_dir in self.__source_dirs:
                    self.walk(partial(add_zip, zip_prefix=Path('python')), source_dir)
                for module in self.__modules:
                    spec = importlib.util.find_spec(module)
                    if spec:
                        if spec.submodule_search_locations:
                            for location in spec.submodule_search_locations:
                                self.walk(partial(add_zip, zip_prefix=Path('python') / module), location)

    def walk(self, fun, root):
        for parent, dirs, files in os.walk(root):
            if parent in self.__exclude_dirs:  # TODO not testing sub exlude dirs
                continue
            for file in files:
                if self.exclude_regexp.match(file) is not None:
                    continue
                fun(root, parent, file)
