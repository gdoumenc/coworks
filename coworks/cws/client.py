import os
import sys
import typing as t
from logging import WARNING, getLogger
from pathlib import Path

import anyconfig
import click
from flask.cli import FlaskGroup
from flask.cli import ScriptInfo

from coworks import __version__
from coworks.utils import DEFAULT_DEV_WORKSPACE
from coworks.utils import DEFAULT_PROJECT_DIR
from coworks.utils import PROJECT_CONFIG_VERSION
from coworks.utils import get_app_workspace
from coworks.utils import get_system_info
from coworks.utils import import_attr
from .deploy import deploy_command
from .deploy import deployed_command
from .deploy import destroy_command
from .new import new_command
from .zip import zip_command


class CwsContext(click.Context):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__project_dir = None
        self.__project_dir_added_in_path = False

    def add_project_dir(self, project_dir):
        self.__project_dir = project_dir

    def __enter__(self):
        if self.__project_dir:
            os.environ['CWS_PROJECT_DIR'] = self.__project_dir
            if self.__project_dir not in sys.path:
                sys.path.insert(0, self.__project_dir)
                self.__project_dir_added_in_path = True
        return super().__enter__()

    def __exit__(self, *args):
        if self.__project_dir:
            os.environ.pop('CWS_PROJECT_DIR', None)
            if self.__project_dir_added_in_path:
                sys.path.remove(self.__project_dir)
                self.__project_dir_added_in_path = False
        super().__exit__(*args)


class CoWorksGroup(FlaskGroup):

    def __init__(self, add_default_commands=True, **kwargs):
        super().__init__(add_version_option=False, load_dotenv=False, **kwargs)
        self.context_class = CwsContext
        if add_default_commands:
            self.add_command(t.cast("Command", new_command))
            self.add_command(t.cast("Command", deploy_command))
            self.add_command(t.cast("Command", destroy_command))
            self.add_command(t.cast("Command", deployed_command))
            self.add_command(t.cast("Command", zip_command))

    def make_context(self, info_name, args, parent=None, **kwargs):
        ctx: CwsContext = t.cast(CwsContext, super().make_context(info_name, args, **kwargs))

        # Warning for deprecated options and echo stage
        if "FLASK_ENV" in os.environ:
            print(
                "\x1b[1m\x1b[31m'FLASK_ENV' is deprecated. Use 'CWS_STAGE' instead.\x1b[0m",
                file=sys.stderr,
            )
        click.echo(f" * Workspace: {get_app_workspace()}")

        # Get project infos
        config_file = ctx.params.get('config_file')
        config_file_suffix = ctx.params.get('config_file_suffix')
        project_dir = ctx.params.get('project_dir')
        if project_dir:
            ctx.add_project_dir(project_dir)

        # Adds environment variables and defined commands from project file
        with ctx:
            project_config = ProjectConfig(project_dir, config_file, config_file_suffix)
            commands = project_config.get_commands(get_app_workspace())
            if commands:
                for name, options in commands.items():
                    cmd_class_name = options.pop('class', None)
                    if cmd_class_name:
                        splitted = cmd_class_name.split('.')
                        cmd = import_attr('.'.join(splitted[:-1]), splitted[-1])

                        # Sets option's value as default command param
                        # (may then be forced in command line or defined by default)
                        for param in cmd.params:
                            if param.name in options:
                                param.default = options.get(param.name)

                        self.add_command(cmd, name)

        return ctx

    def get_command(self, ctx, name):
        """Wrapper to help debug import error."""
        try:
            info = ctx.ensure_object(ScriptInfo)
            info.load_app()
        except Exception as e:
            if getattr(e, '__cause__'):
                print(e.__cause__)
        return super().get_command(ctx, name)


@click.group(cls=CoWorksGroup)
@click.version_option(version=__version__, message=f'%(prog)s %(version)s, {get_system_info()}')
@click.option('-s', '--stage', default=DEFAULT_DEV_WORKSPACE, help="Stage environment.")
@click.option('-p', '--project-dir', default=DEFAULT_PROJECT_DIR,
              help=f"The project directory path (absolute or relative) [default to '{DEFAULT_PROJECT_DIR}'].")
@click.option('-c', '--config-file', default='project', help="Configuration file path [relative from project dir].")
@click.option('--config-file-suffix', default='.cws.yml', help="Configuration file suffix.")
@click.pass_context
def client(*args, **kwargs):
    ...


class ProjectConfig:
    """Class for the project configuration file."""

    def __init__(self, project_dir, file_name, file_suffix):
        getLogger('anyconfig').setLevel(WARNING)
        self.project_dir = project_dir
        try:
            self.params = self._load_config(project_dir, file_name, file_suffix)
        except TypeError:
            raise RuntimeError(f"Cannot find project coniguration file in {project_dir}")
        if self.params and self.params.get('version', PROJECT_CONFIG_VERSION) != PROJECT_CONFIG_VERSION:
            raise RuntimeError(f"Wrong project file version (should be {PROJECT_CONFIG_VERSION}).\n")

    def get_commands(self, workspace):
        """ Returns the list of commands defined for this microservice."""
        commands = self.params.get('commands', {})

        # Commands may be redefined in the specific workspace
        workspaces = self.params.get('workspaces', {})
        if workspace in workspaces:
            specific_workspace_commands = workspaces[workspace].get('commands', {})
            for cmd, options in specific_workspace_commands.items():
                commands[cmd].update(options)

        return commands

    @staticmethod
    def _load_config(project_dir, file_name, file_suffix):
        """Loads the project configuration file."""

        def load(dir):
            project_dir_path = Path(dir)
            project_file = project_dir_path / (file_name + file_suffix)
            return anyconfig.load(project_file, ac_ignore_missing=True)

        params = load(project_dir)
        if not params:
            params = load('.')

        return params
