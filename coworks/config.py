from dataclasses import dataclass
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

    def setdefault(self, key, value):
        """Same as for dict."""
        if not hasattr(self, key):
            setattr(self, key, value)
