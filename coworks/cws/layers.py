import importlib.util
import os
import re
import shutil

from functools import partial
from pathlib import Path
from typing import Optional, Iterable
from zipfile import ZipFile
from subprocess import run
from tempfile import TemporaryDirectory

from SCons import Environment
from SCons.Builder import Builder

EXCLUDE_FILE_PATTERN = r".*.py[co]"


class Layer:

    def __init__(self, layer_zipfilename: str,
                 modules: Optional[Iterable] = None,
                 source_dirs: Optional[Iterable] = None,
                 exclude_dirs: Optional[Iterable] = None,
                 exclude_file_pattern: str = None,
                 requirements_path: str = None):
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
        self.__modules = modules
        self.__exclude_dirs = exclude_dirs or []
        self.__exclude_file_pattern = exclude_file_pattern
        self.__exclude_regexp = None
        self.__requirements_path = requirements_path

        env = Environment.Base(BUILDERS={'Layer': Builder(action=partial(self.generate_zip_file, target=self))})

        def add_dep(_, root, file):
            dependencies.append(Path(root) / file)

        dependencies = []
        for source_dir in self.__source_dirs:
            self.walk(add_dep, source_dir)

        if self.__modules:
            for module in self.__modules:
                spec = importlib.util.find_spec(module)
                if spec:
                    if spec.submodule_search_locations:
                        for location in spec.submodule_search_locations:
                            self.walk(add_dep, location)
            print([file.as_posix() for file in dependencies])
            env.Layer(layer_zipfilename, [file.as_posix() for file in dependencies])
        else:
            for zip_filename in layer_zipfilename:
                Layer.generate_layer_from_requirements(zip_filename, self.__requirements_path)

    @staticmethod
    def generate_layer_from_requirements(zip_filename, requirements_path):
        with TemporaryDirectory() as temp_dir:
            python_temp_dir = os.path.join(temp_dir, 'python')
            os.makedirs(python_temp_dir)
            run(f"pip install -r {requirements_path} -t {python_temp_dir}", shell=True)
            if zip_filename[-4:] == '.zip':
                zip_filename = zip_filename[:-4]  # shutil.make_archive automatically adds .zip extension
            shutil.make_archive(zip_filename, 'zip', temp_dir)

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
