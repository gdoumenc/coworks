from dataclasses import dataclass, field
from typing import Callable, Union, List

from chalice import CORSConfig as ChaliceCORSConfig
from chalice.app import AuthRequest, AuthResponse

from .mixins import CoworksMixin


class CORSConfig(ChaliceCORSConfig):

    def get_access_control_headers(self):
        if not self.allow_origin:
            return {}
        return super().get_access_control_headers()


DEFAULT_WORKSPACE = 'dev'


@dataclass
class Config:
    """ Configuration class for deployment.

    """

    workspace: str = DEFAULT_WORKSPACE
    debug: bool = False
    version: str = ""

    #: Variables defined for the Lambda
    environment_variables_file: str = None
    layers: List[str] = field(default_factory=list)

    #: Variable defined in the staged API
    api_variables_file: str = None

    auth: Callable[[CoworksMixin, AuthRequest], Union[bool, list, AuthResponse]] = None
    cors: CORSConfig = CORSConfig(allow_origin='')
    timeout: int = 60
