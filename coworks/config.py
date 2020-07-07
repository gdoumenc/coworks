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

    @property
    def environment_variables_file_secret(self):
        return str(Path(self.environment_variables_file).with_suffix(SECRET_ENV_FILE_SUFFIX))

    def load_environment_variables(self, project_dir):
        if self.environment_variables_file:
            parent = Path(project_dir)
            var_file = Path(self.environment_variables_file)

            if var_file.suffix != '.json':
                raise FileNotFoundError(f"Environment variables file has not a JSON extension: {var_file}.\n")

            self._load_file(parent / var_file.with_suffix(ENV_FILE_SUFFIX), must_exist=True)
            self._load_file(parent / var_file.with_suffix(SECRET_ENV_FILE_SUFFIX), must_exist=False)

    def _load_file(self, var_file, *, must_exist):
        try:
            with open(var_file) as f:
                os.environ.update(json.loads(f.read()))
        except FileNotFoundError:
            if must_exist:
                raise FileNotFoundError(f"Cannot find environment file {var_file} for workspace {self.workspace}.\n")
        except JSONDecodeError as e:
            raise FileNotFoundError(f"Syntax error when in e{var_file}: {str(e)}.\n")
        except Exception as e:
            print(type(e))
            raise FileNotFoundError(f"Error when loading environment variables files {str(e)}.\n")

    def setdefault(self, key, value):
        """Same as for dict."""
        if not hasattr(self, key):
            setattr(self, key, value)
