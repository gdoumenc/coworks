import dataclasses
import json
import os
import re
import typing as t
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path

DEFAULT_PROJECT_DIR = '.'
DEFAULT_LOCAL_WORKSPACE = 'local'
DEFAULT_DEV_WORKSPACE = 'dev'

ENV_FILE_SUFFIX = '.json'
SECRET_ENV_FILE_SUFFIX = '.secret.json'


@dataclass
class Config:
    """ Configuration class for deployment."""

    workspace: str = DEFAULT_DEV_WORKSPACE
    environment_variables_file: t.Union[str, t.List[str], Path, t.List[Path]] = 'vars.json'
    environment_variables: t.Union[dict, t.List[dict]] = None

    bizz_bucket_header_key: str = 'X-CWS-S3Bucket'
    bizz_key_header_key: str = 'X-CWS-S3Key'

    @property
    def ENV(self):
        return self.workspace

    def is_valid_for(self, workspace: str) -> bool:
        return self.workspace == workspace

    def existing_environment_variables_files(self, app):
        """Returns a list containing the paths to environment variables files that actually exist """

        # store in a dict to allow specific environment variable files to be overloaded
        files = {}

        def add_file(_dir):
            for file in environment_variables_file:
                var_file = Path(_dir) / file
                if var_file.is_file():
                    files[file] = var_file
                var_secret_file = var_file.with_suffix(SECRET_ENV_FILE_SUFFIX)
                if var_secret_file.is_file():
                    files[var_secret_file] = var_secret_file

        environment_variables_file = as_list(self.environment_variables_file)

        # get default then specific
        app.logger.debug(f"Searching environment variable in {app.root_path}")
        add_file(app.root_path)
        app.logger.debug(f"Searching environment variable in {app.instance_path}")
        add_file(app.instance_path)
        return [f.as_posix() for f in files.values()]

    def load_environment_variables(self, app):
        """Uploads environment variables from the environment variables files and variables."""
        environment_variables = {}

        # Environment variables from files and from config
        for file in self.existing_environment_variables_files(app):
            try:
                with Path(file).open() as f:
                    environment_variables.update(json.loads(f.read()))
            except JSONDecodeError as e:
                raise FileNotFoundError(f"Syntax error in file {file}: {str(e)}.\n")

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
                app.config[key] = value

    def setdefault(self, key, value):
        """Same as for dict."""
        if not hasattr(self, key):
            setattr(self, key, value)

    def asdict(self):
        return dataclasses.asdict(self)


class LocalConfig(Config):
    """ Production configuration have workspace's name corresponding to version's index."""

    def __init__(self, workspace: str = DEFAULT_LOCAL_WORKSPACE, **kwargs):
        super().__init__(workspace=workspace, **kwargs)
        self.environment_variables = {
            'AWS_XRAY_SDK_ENABLED': False,
            'EXPLAIN_TEMPLATE_LOADING': True,
        }


class DevConfig(Config):
    """ Production configuration have workspace's name corresponding to version's index."""

    def __init__(self, workspace: str = DEFAULT_DEV_WORKSPACE, **kwargs):
        super().__init__(workspace=workspace, **kwargs)


class ProdConfig(DevConfig):
    """ Production configuration have workspace's name corresponding to version's index."""

    def __init__(self, pattern: str = r"[vV][1-9]+", **kwargs):
        super().__init__(**kwargs)
        self.pattern = pattern

    def is_valid_for(self, workspace: str):
        return re.match(self.pattern, workspace) is not None


def as_list(var):
    if var is None:
        return []
    if type(var) is list:
        return var
    return [var]
