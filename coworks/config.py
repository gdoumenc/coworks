from dataclasses import dataclass
from typing import Callable, Union

from chalice import CORSConfig as ChaliceCORSConfig
from chalice.app import AuthRequest, AuthResponse


class CORSConfig(ChaliceCORSConfig):

    def get_access_control_headers(self):
        if not self.allow_origin:
            return {}
        return super().get_access_control_headers()


@dataclass
class Config:
    """ Configuration class for deployment.

    """

    workspace_name: str = "dev"

    authorizer: Callable[['TechMicroService', AuthRequest], Union[bool, list, AuthResponse]] = None
    cors: CORSConfig = CORSConfig(allow_origin='')
    timeout: int = 60

    #: Variables defined for the Lambda
    environment_variables_file: str = None

    #: Variable defined in the staged API
    stage_variables_file: str = None
