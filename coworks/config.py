import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Union

from chalice import CORSConfig as ChaliceCORSConfig
from chalice.app import AuthRequest, AuthResponse

from .mixins import CoworksMixin

DEFAULT_PROJECT_DIR = '.'
DEFAULT_WORKSPACE = 'dev'


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

    def load_environment_variables(self, project_dir):
        if self.environment_variables_file:
            var_file = Path(project_dir) / self.environment_variables_file
            try:
                with open(var_file) as f:
                    os.environ.update(json.loads(f.read()))
            except FileNotFoundError:
                workspace = self.workspace
                raise FileNotFoundError(f"Cannot find environment file {var_file} for workspace {workspace}.")
            except Exception:
                raise FileNotFoundError(f"No wrokspace defined in config.")


    def setdefault(self, key, value):
        """Same as for dict."""
        if not hasattr(self, key):
            setattr(self, key, value)
