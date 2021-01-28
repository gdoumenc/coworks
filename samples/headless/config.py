from dataclasses import dataclass, field

from coworks.config import Config as CwsConfig, CORSConfig


@dataclass
class Config(CwsConfig):
    environment_variables_file: str = "vars.json"


@dataclass
class LocalConfig(Config):
    workspace: str = 'local'
    environment_variables: dict = field(
        default_factory=lambda: {'ASSETS_URL': "", "AWS_XRAY_SDK_ENABLED": False}
    )


@dataclass
class DevConfig(Config):
    workspace: str = 'dev'
    environment_variables: dict = field(
        default_factory=lambda: {'ASSETS_URL': "https://draft.morassuti.com"}
    )
    cors: CORSConfig = CORSConfig(allow_origin='*', max_age=600)


@dataclass
class ProdConfig(Config):
    workspace: str = 'prod'
    environment_variables: dict = field(
        default_factory=lambda: {'ASSETS_URL': "https://www.morassuti.com"}
    )
    cors: CORSConfig = CORSConfig(allow_origin='*', max_age=600)
