import json
import os
import re
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
        environment_variables = {}

        # Environment variables from files and from config
        for file in self.existing_environment_variables_files(project_dir):
            environment_variables.update(self._load_file(file))
        if self.environment_variables:
            environment_variables.update(self.environment_variables)

        # Check environment variables name are accepted by AWS
        # Keys start with a letter and are at least two characters.
        # Keys only contain letters, numbers, and the underscore character (_).
        var_name_regexp = re.compile(r'[a-zA-Z][a-zA-Z_]+')
        for key in environment_variables:
            if not var_name_regexp.fullmatch(key):
                raise KeyError(f'Wrong environment variable name: {key}')

        # Set environment variables
        if environment_variables:
            for key, value in environment_variables.items():
                os.environ[key] = str(value)

    def setdefault(self, key, value):
        """Same as for dict."""
        if not hasattr(self, key):
            setattr(self, key, value)

    @staticmethod
    def _load_file(var_file):
        try:
            with var_file.open() as f:
                return json.loads(f.read())
        except JSONDecodeError as e:
            raise FileNotFoundError(f"Syntax error when in e{var_file}: {str(e)}.\n")
        except Exception as e:
            print(type(e))
            raise FileNotFoundError(f"Error when loading environment variables files {str(e)}.\n")
