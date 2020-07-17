import json
import os
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Callable, Union

from chalice import CORSConfig as ChaliceCORSConfig
from chalice.app import AuthRequest, AuthResponse

from .mixins import CoworksMixin

DEFAULT_PROJECT_DIR = '.'
DEFAULT_WORKSPACE = 'dev'

ENV_FILE_SUFFIX = '.json'
SECRET_ENV_FILE_SUFFIX = '.secret.json'


class CORSConfig(ChaliceCORSConfig):

    def get_access_control_headers(self):
        if not self.allow_origin:
            return {}
        return super().get_access_control_headers()


@dataclass
class Config:
    """ Configuration class for deployment."""

    version: str = ""
    workspace: str = DEFAULT_WORKSPACE
    environment_variables_file: str = None
    auth: Callable[[CoworksMixin, AuthRequest], Union[bool, list, AuthResponse]] = None
    cors: CORSConfig = CORSConfig(allow_origin='')
    data: dict = None

    def existing_environment_variables_files(self, project_dir):
        """Returns a list containing the paths to environment variables files that acually exist """
        if self.environment_variables_file is None:
            return []
        else:
            parent = Path(project_dir)
            var_file = parent / self.environment_variables_file
            var_secret_file = var_file.with_suffix(SECRET_ENV_FILE_SUFFIX)
            files = []
            if var_file.is_file():
                files.append(var_file)
            if var_secret_file.is_file():
                files.append(var_secret_file)
            return files

    def load_environment_variables(self, project_dir):
        """Uploads environment variables from the environment variables files."""
        for file in self.existing_environment_variables_files(project_dir):
            self._load_file(file)

    def setdefault(self, key, value):
        """Same as for dict."""
        if not hasattr(self, key):
            setattr(self, key, value)

    @staticmethod
    def _load_file(var_file):
        try:
            with var_file.open() as f:
                os.environ.update(json.loads(f.read()))
        except JSONDecodeError as e:
            raise FileNotFoundError(f"Syntax error when in e{var_file}: {str(e)}.\n")
        except Exception as e:
            print(type(e))
            raise FileNotFoundError(f"Error when loading environment variables files {str(e)}.\n")
