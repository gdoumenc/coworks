import os
import sys
import types
import typing as t
from contextlib import contextmanager
from logging import WARNING
from logging import getLogger
from pathlib import Path

import anyconfig
import click
import flask
from click import UsageError
from flask.cli import ScriptInfo

from coworks import __version__
from coworks.utils import DEFAULT_DEV_STAGE
from coworks.utils import DEFAULT_PROJECT_DIR
from coworks.utils import PROJECT_CONFIG_VERSION
from coworks.utils import get_app_stage
from coworks.utils import get_system_info
from coworks.utils import import_attr
from coworks.utils import load_dotenv
from coworks.utils import show_stage_banner
from .deploy import deploy_command
from .deploy import deployed_command
from .deploy import destroy_command
from .new import new_command
from .zip import zip_command


class CwsScriptInfo(ScriptInfo):

    def __init__(self, project_dir=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_dir = project_dir
        self.__dotenv_loaded = False

    @property
    def project_dir(self):
        return self.__project_dir

    @project_dir.setter
    def project_dir(self, project_dir):
        self.__project_dir = Path(project_dir).absolute().as_posix() if project_dir else None

    @contextmanager
    def project_context(self, ctx=None):
        if not self.__dotenv_loaded:
            workspace = get_app_stage()
            load_dotenv(workspace)
            self.__dotenv_loaded = True

        old_dir = os.getcwd()
        try:
            os.chdir(self.project_dir)
        except OSError as e:
            if not ctx:
                raise UsageError(f"Project dir {self.project_dir} not found.")
        finally:
            yield
            os.chdir(old_dir)

    def load_app(self):
        with self.project_context():
            return super().load_app()


def _set_stage(ctx, param, value):
    if value is not None:
        os.environ["CWS_STAGE"] = value
        return value


_stage_option = click.Option(
    ["-S", "--stage"],
    help=(
        f"The CoWorks stage (default {DEFAULT_DEV_STAGE})."
    ),
    is_eager=True,
    expose_value=False,
    callback=_set_stage,
)


class CwsGroup(flask.cli.FlaskGroup):

    def __init__(self, add_default_commands=True, **extra):
        params = list(extra.pop("params", None) or ())
        params.append(_stage_option)
        extra["add_version_option"] = False
        extra["load_dotenv"] = False
        super().__init__(params=params, **extra)

        if add_default_commands:
            self.add_command(t.cast("Command", new_command))
            self.add_command(t.cast("Command", deploy_command))
            self.add_command(t.cast("Command", destroy_command))
            self.add_command(t.cast("Command", deployed_command))
            self.add_command(t.cast("Command", zip_command))

    def make_context(self, info_name, args, parent=None, **kwargs):

        # Warning for deprecated options and echo stage
        if "FLASK_ENV" in os.environ:
            click.echo(
                "\x1b[1m\x1b[31m'FLASK_ENV' is deprecated. Use 'CWS_STAGE' or '-S' option instead.\x1b[0m",
                file=sys.stderr,
            )

        # Get project infos
        script_info = CwsScriptInfo(create_app=self.create_app, set_debug_flag=self.set_debug_flag)
        if 'obj' not in kwargs:
            ctx = super().make_context(info_name, args, obj=script_info, **kwargs)
        else:
            ctx = super().make_context(info_name, args, **kwargs)
        config_file = ctx.params.get('config_file')
        config_file_suffix = ctx.params.get('config_file_suffix')
        project_dir = ctx.params.get('project_dir')
        if project_dir:
            script_info.project_dir = project_dir

        # Adds environment variables and defined commands from project file
        project_config = ProjectConfig(project_dir, config_file, config_file_suffix)
        with script_info.project_context(ctx):
            commands = project_config.get_commands(get_app_stage())
            if commands:
                for name, options in commands.items():
                    cmd_class_name = options.pop('class', None)
                    if cmd_class_name:
                        cmd_module, cmd_class = cmd_class_name.rsplit('.', 1)
                        try:
                            cmd = import_attr(cmd_module, cmd_class)
                        except ModuleNotFoundError as e:
                            raise click.UsageError(f"Cannot load command {cmd_class!r} in module {cmd_module!r}.")
                    elif name in self.commands:
                        cmd = self.commands[name]
                    else:
                        raise click.UsageError(f"The command {name} is undefined or the class option is missing.")

                    # Sets option's value as default command param
                    # (may then be forced in command line or defined by default)
                    for param in cmd.params:
                        if param.name in options:
                            param.default = options.get(param.name)

                    self.add_command(cmd, name)

        return ctx


@click.group(cls=CwsGroup)
@click.version_option(version=__version__, message=f'%(prog)s %(version)s, {get_system_info()}')
@click.option('-p', '--project-dir', default=DEFAULT_PROJECT_DIR,
              help=f"The project directory path (absolute or relative) [default to '{DEFAULT_PROJECT_DIR}'].")
@click.option('-c', '--config-file', default='project', help="Configuration file path [relative from project dir].")
@click.option('--config-file-suffix', default='.cws.yml', help="Configuration file suffix.")
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


def overriden_run_banner():
    """Copy the original function and add stage banner."""
    show_server_banner_copy = types.FunctionType(flask.cli.show_server_banner.__code__,
                                                 flask.cli.show_server_banner.__globals__,
                                                 name=flask.cli.show_server_banner.__name__,
                                                 argdefs=flask.cli.show_server_banner.__defaults__,
                                                 closure=flask.cli.show_server_banner.__closure__)

    def show_banner_with_stage(*args):
        show_stage_banner()
        show_server_banner_copy(*args)

    return show_banner_with_stage


# Overrides run banner function to add stage value
flask.cli.show_server_banner = overriden_run_banner()
