from dataclasses import dataclass, field

from coworks.config import Config as CwsConfig


@dataclass
class Config(CwsConfig):
    environment_variables_file: str = "vars.json"


@dataclass
class LocalConfig(Config):
    # environment_variables: dict = field(default_factory=lambda: {"AWS_XRAY_SDK_ENABLED": False})
    workspace: str = 'local'
    environment_variables: dict = field(
        default_factory=lambda: {'ASSETS_URL': ""}
    )


@dataclass
class DevConfig(Config):
    workspace: str = 'dev'
    environment_variables: dict = field(
        default_factory=lambda: {'ASSETS_URL': "https://d2ix7tgbgr2hm8.cloudfront.net"}
    )


@dataclass
class ProdConfig(Config):
    workspace: str = 'prod'
    environment_variables: dict = field(
        default_factory=lambda: {'ASSETS_URL': "https://d2ix7tgbgr2hm8.cloudfront.net"}
    )
