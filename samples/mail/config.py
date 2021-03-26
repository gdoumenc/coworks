from dataclasses import dataclass
from typing import Any

from coworks.config import Config as CwsConfig


@dataclass
class Config(CwsConfig):
    environment_variables_file: str = "vars.json"


@dataclass
class LocalConfig(Config):
    root: str = ''
    workspace: str = 'local'
    auth: Any = lambda _, __: True


@dataclass
class DevConfig(Config):
    workspace: str = 'dev'
