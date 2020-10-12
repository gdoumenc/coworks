import json
import os
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Callable, Union, List, Tuple, Any

from chalice import CORSConfig as ChaliceCORSConfig
from chalice.app import AuthRequest as ChaliceAuthRequest

from .mixins import CoworksMixin
from .utils import as_list

DEFAULT_PROJECT_DIR = '.'
DEFAULT_WORKSPACE = 'dev'

ENV_FILE_SUFFIX = '.json'
SECRET_ENV_FILE_SUFFIX = '.secret.json'


class AuthRequest(ChaliceAuthRequest):
    def __init__(self, auth_type, token, method_arn):
        self.auth_type = auth_type
        self.token = token
        self.method_arn = method_arn

        _, self.workspace, self.method, self.route = method_arn.split('/', 3)


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
    environment_variables_file: Union[str, List[str]] = None
    environment_variables: Union[dict, List[dict]] = None
    auth: Callable[[CoworksMixin, AuthRequest], Any] = None
    cors: CORSConfig = CORSConfig(allow_origin='')
    content_type: Tuple[str] = ('multipart/form-data', 'application/json', 'text/plain')
    data: dict = None

    def existing_environment_variables_files(self, project_dir):
        """Returns a list containing the paths to environment variables files that actually exist """
        environment_variables_file = as_list(self.environment_variables_file)
        files = []
        parent = Path(project_dir)
        for file in environment_variables_file:
            var_file = parent / file
            if var_file.is_file():
                files.append(var_file)
            var_secret_file = var_file.with_suffix(SECRET_ENV_FILE_SUFFIX)
            if var_secret_file.is_file():
                files.append(var_secret_file)
        return files

    def load_environment_variables(self, project_dir):
        """Uploads environment variables from the environment variables files and variables."""
        for file in self.existing_environment_variables_files(project_dir):
            self._load_file(file)

        if self.environment_variables:
            for key, value in self.environment_variables.items():
                os.environ[key] = str(value)

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
