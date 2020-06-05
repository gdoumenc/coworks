import importlib.util
import os
from pathlib import Path
from zipfile import ZipFile
import re

from SCons import Environment
from SCons.Builder import Builder


# noinspection PyPep8Naming
def Layer(filename='layer.zip', source_dirs=None, modules=None, exclude_dirs=None, exclude_file_pattern=None):
    env = Environment.Base(BUILDERS={'Layer': Builder(action=generate_zip_file)}, SRC_DIRS=source_dirs,
                           MODULES=modules, EXCLUDE_DIRS=exclude_dirs, EXCLUDE_FILE_PATTERN=exclude_file_pattern)
    env.Layer(filename, [])


def generate_zip_file(target, source, env=None):
    modules = env['MODULES']
    source_dirs = env['SRC_DIRS']
    exclude_dirs = env['EXCLUDE_DIRS']
    exclude_file_pattern = env['EXCLUDE_FILE_PATTERN']

    with ZipFile(target[0].name, mode='w') as layer_zip:
        for source_dir in source_dirs:
            src_dir = Path(source_dir)
            for root, dirs, files in os.walk(source_dir):
                if root in exclude_dirs:
                    continue
                for file in files:
                    if file.endswith(('.pyc', '.pyo')):
                        continue
                    if exclude_file_pattern and re.match(exclude_file_pattern, file) is not None:
                        continue
                    layer_zip.write(src_dir / root / file, Path('python') / root / file)

        for module in modules:
            spec = importlib.util.find_spec(module)
            for filename in spec.loader.contents():
                if spec.loader.is_resource(filename):
                    arcname = Path('python') / spec.name / filename
                    layer_zip.write(spec.loader.open_resource(filename), arcname)
