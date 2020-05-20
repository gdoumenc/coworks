import os
import pathlib
import re
import sys
from zipfile import ZipFile

from SCons import Environment
from SCons.Builder import Builder


# noinspection PyPep8Naming

def Layer(filename='layer.zip', source_dirs=None, modules=None, exclude_dirs=None, exclude_file_pattern=None):
    env = Environment.Base(BUILDERS={'Layer': Builder(action=generate_zip_file)}, SRC_DIRS=source_dirs,
                           MODULES=modules, EXCLUDE_DIRS=exclude_dirs, EXCLUDE_FILE_PATTERN=exclude_file_pattern)
    env.Layer(filename, [])


def generate_zip_file(target, source, env=None):
    source_dirs = env['SRC_DIRS']
    modules = env['MODULES']
    exclude_dirs = env['EXCLUDE_DIRS']
    exclude_file_pattern = env['EXCLUDE_FILE_PATTERN']

    source_dirs = source_dirs or [path for path in sys.path if os.path.basename(path) == 'site-packages']
    if type(source_dirs) is not list:
        source_dirs = [source_dirs]

    exclude_dirs = exclude_dirs or ['__pycache__', 'pip', 'botocore', 'boto3', 'click', 'docutils', 'tests']
    exclude_file_pattern = exclude_file_pattern or r'.*[.]pyc'
    for source_dir in source_dirs:
        with ZipFile(target[0].name, mode='w') as layer_zip:
            for root, dirs, files in os.walk(source_dir):
                pathes = pathlib.Path(os.path.relpath(root, source_dir))
                if any(part in exclude_dirs for part in pathes.parts):
                    continue

                if modules and root not in modules:
                    continue

                for file in files:
                    if re.match(exclude_file_pattern, file) is not None:
                        continue
                    filename = os.path.join(root, file)
                    if os.path.isfile(filename):  # regular files only
                        arcname = os.path.join('python', os.path.relpath(filename, source_dir))
                        layer_zip.write(filename, arcname)
            for root, dirs, files in os.walk('/home/studiogdo/workspace/coworks/coworks'):
                # add directory (needed for empty dirs)
                # layer_zip.write(root, os.path.relpath(root, relroot))
                for file in files:
                    if re.match(exclude_file_pattern, file) is not None:
                        continue
                    filename = os.path.join(root, file)
                    if os.path.isfile(filename):  # regular files only
                        arcname = os.path.join('python', os.path.relpath(filename, '/home/studiogdo/workspace/coworks'))
                        layer_zip.write(filename, arcname)
