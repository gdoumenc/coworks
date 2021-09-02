from logging import WARNING, getLogger

import anyconfig
import click
import os
from flask.cli import FlaskGroup
from pathlib import Path

from ..config import DEFAULT_PROJECT_DIR, DEFAULT_WORKSPACE
from ..utils import get_system_info, import_attr
from ..version import __version__

PROJECT_CONFIG_VERSION = 3


class CoWorksGroup(FlaskGroup):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, add_version_option=False, **kwargs)

    def make_context(self, info_name, args, parent=None, **kwargs):
        ctx = super().make_context(info_name, args, **kwargs)

        # Get project infos
        config_file = ctx.params.get('config_file')
        config_file_suffix = ctx.params.get('config_file_suffix')
        project_dir = ctx.params.get('project_dir')
        workspace = ctx.params.get('workspace')
        if workspace:
            os.environ['WORKSPACE'] = workspace

        # Adds defined commands from project file
        project_config = ProjectConfig(project_dir, config_file, config_file_suffix)
        for name, options in project_config.all_commands.items():
            cmd_class_name = options.pop('class')
            if cmd_class_name:
                splitted = cmd_class_name.split('.')
                cmd = import_attr('.'.join(splitted[:-1]), splitted[-1], cwd=project_dir)

                # Sets options value as default command param (may then be forced in command line or defined by default)
                for param in cmd.params:
                    if param.name in options:
                        param.default = options.get(param.name)

                self.add_command(cmd, name)

        return ctx


@click.group(cls=CoWorksGroup)
@click.version_option(version=__version__, message=f'%(prog)s %(version)s, {get_system_info()}')
@click.option('-p', '--project-dir', default=DEFAULT_PROJECT_DIR,
              help=f"The project directory path (absolute or relative) [default to '{DEFAULT_PROJECT_DIR}'].")
@click.option('-c', '--config-file', default='project', help="Configuration file path [path from project dir].")
@click.option('--config-file-suffix', default='.cws.yml', help="Configuration file suffix.")
@click.option('-w', '--workspace', default=DEFAULT_WORKSPACE,
              help=f"Application stage [default to '{DEFAULT_WORKSPACE}'].")
@click.pass_context
def client(*args, **kwargs):
    ...


class ProjectConfig:
    """Class for the project configuration file."""

    def __init__(self, project_dir, file_name, file_suffix):
        getLogger('anyconfig').setLevel(WARNING)
        self.project_dir = project_dir
        self.params = self._load_config(project_dir, file_name, file_suffix)
        if not self.params:
            raise RuntimeError(f"Cannot find project file ({file_name + file_suffix}).\n")
        if self.params.get('version') != PROJECT_CONFIG_VERSION:
            raise RuntimeError(f"Wrong project file version (should be {PROJECT_CONFIG_VERSION}).\n")

    @property
    def all_commands(self):
        """ Returns the list of microservices on which the command will be executed."""
        return self.params.get('commands', {})

    @staticmethod
    def _load_config(project_dir, file_name, file_suffix):
        """Loads the project configuration file."""

        def load(dir):
            project_dir_path = Path(dir)
            project_file = project_dir_path / (file_name + file_suffix)
            project_secret_file = project_dir_path / (file_name + '.secret' + file_suffix)
            return anyconfig.multi_load([project_file, project_secret_file], ac_ignore_missing=True)

        params = load(project_dir)
        if not params:
            params = load('.')

        return params
