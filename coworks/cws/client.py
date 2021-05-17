from copy import deepcopy
from dataclasses import dataclass, asdict
from logging import getLogger, WARNING

import anyconfig
import click
import sys
from pathlib import Path
from typing import List, Tuple

from .command import CwsMultiCommands
from .error import CwsClientError
from ..config import DEFAULT_PROJECT_DIR, DEFAULT_WORKSPACE
from ..utils import import_attr, get_system_info
from ..version import __version__

PROJECT_CONFIG_VERSION = 2


@click.group()
@click.version_option(version=__version__, message=f'%(prog)s %(version)s, {get_system_info()}')
@click.option('-p', '--project-dir', default=DEFAULT_PROJECT_DIR,
              help=f"The project directory path (absolute or relative) [default to '{DEFAULT_PROJECT_DIR}'].")
@click.option('-c', '--config-file', help="Configuration file path [path from project dir].")
@click.option('-m', '--module', help="Filename of your microservice python source file.")
@click.option('-s', '--service', help="Microservice variable name in the source file.")
@click.option('-w', '--workspace', default=DEFAULT_WORKSPACE,
              help=f"Application stage [default to '{DEFAULT_WORKSPACE}'].")
@click.pass_context
def client(*args, **kwargs):
    ...


def invoke(ctx):
    """Invokes the command over the service or the declared services in project configuration file."""
    try:
        args = ctx.args
        protected_args = ctx.protected_args
        if not protected_args:
            sys.stderr.write(str("No command given.\n"))
            client.main(['--help'])
            sys.exit(1)
        command_name = protected_args[0]

        # get project options
        cws_options = CwsClientOptions(ctx.params)
        if not cws_options.services:
            sys.stderr.write(str("Nothing to execute as no service defined.\n"))
            sys.exit(1)
        project_dir = cws_options.project_dir
        workspace = cws_options.workspace

        # Iterates over the declared services in project configuration file
        commands_to_be_executed = CwsMultiCommands()
        for module, service in cws_options.services:
            ctx.args = list(args)
            ctx.protected_args = protected_args

            # Get command from the microservice description
            handler = cws_options.get_handler(module, service)
            handler.deferred_init(workspace)
            service_config = cws_options.get_service_config(module, service)
            command = service_config.get_command(command_name, handler)
            if not command:
                raise CwsClientError(f"Undefined command {command_name}.\n")
            command_options = service_config.get_command_options(command_name)

            # Get user defined options and convert them in right types
            client_options, _, cmd_opts = command.make_parser(ctx).parse_args(ctx.args)
            for opt_key, opt_value in client_options.items():
                cmd_opt = next(x for x in cmd_opts if x.name == opt_key)
                client_options[opt_key] = cmd_opt.type(opt_value)

            # Adds command and global options
            options = {**command_options, **client_options, '_from_cws': True}
            if options.get('help', False):
                print(command.get_help(ctx))
                return
            command.make_context(command.name, options)
            commands_to_be_executed.append(command, options)

        # Executes all commands
        for command_class, execution_list in commands_to_be_executed.items():
            command_class.multi_execute(project_dir, workspace, execution_list)
    except CwsClientError as client_err:
        sys.stderr.write(f"Error in command: {client_err.msg}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error in command: {str(e)}\n")
        sys.exit(1)


client.invoke = invoke


@dataclass
class CwsClientOptions:
    """Client options defined from click command."""
    project_dir: str
    workspace: str
    module: str
    service: str
    config_file: str
    config_file_suffix: str

    def __init__(self, params):
        self.project_dir = params.get('project_dir')
        self.workspace = params.get('workspace')
        self.module = params.get('module')
        self.service = params.get('service')
        self.config_file = params.get('config_file') or 'project'
        self.config_file_suffix = params.get('config_file_suffix') or '.cws.yml'
        self.project_config = ProjectConfig(self.project_dir, self.config_file, self.config_file_suffix)

    @property
    def services(self):
        """Returns the list of services defined from the client optons."""
        if self.service:
            return [(self.module, self.service)]
        return self.project_config.all_services(self.module)

    def get_handler(self, module, service):
        """Loads microservice handler."""
        try:
            return import_attr(module, service, cwd=self.project_dir)
        except AttributeError as e:
            raise CwsClientError(f"Module '{module}' has no microservice {service} : {str(e)}\n")
        except ModuleNotFoundError as e:
            raise CwsClientError(f"The module '{module}' is not defined in {self.project_dir} : {str(e)}\n")
        except Exception as e:
            raise CwsClientError(f"Error {e} when loading module '{module}'\n")

    def get_service_config(self, module, service, workspace=None):
        """Returns the microserrvice's configuration."""
        workspace = workspace or self.workspace
        return ServiceConfig(self.project_config, module, service, workspace)


class ProjectConfig:
    """Class for the project configuration file."""

    def __init__(self, project_dir, file_name, file_suffix):
        self.project_dir = project_dir
        self.params = {}
        getLogger('anyconfig').setLevel(WARNING)

        # Loads project configuration file at project dir then at root if not found
        self.params = self._load_config(project_dir, file_name, file_suffix)
        if not self.params:
            self.params = self._load_config('.', file_name, file_suffix)

        # Checks results
        if not self.params:
            raise CwsClientError(f"Cannot find project file ({file_name + file_suffix}).\n")
        if self.params.get('version') != PROJECT_CONFIG_VERSION:
            raise CwsClientError(f"Wrong project file version (should be {PROJECT_CONFIG_VERSION}).\n")

    def get_service_config(self, module, service, workspace):
        return ServiceConfig(self, module, service, workspace)

    def all_services(self, module: str = None) -> List[Tuple[str, str]]:
        """ Returns the list of (module, microservice) on which the command will be executed."""
        services = self.params.get('services', {})

        res = []
        for s in services:
            if 'module' not in s or 'services' not in s:
                raise CwsClientError(f"Services wrongly defined.\n")

            if module and s['module'] != module:
                continue

            if 'services' in s:
                _module = s['module']
                _services = s['services']
                if type(_services) is str:
                    res.append((_module, _services))
                else:
                    for service in _services:
                        res.append((_module, service))
        return res

    @property
    def all_commands(self):
        """ Returns the list of microservices on which the command will be executed."""
        return self.params.get('commands', {})

    @staticmethod
    def _load_config(dir, file_name, file_suffix):
        """Loads the project configuration file."""
        project_dir_path = Path(dir)
        project_file = project_dir_path / (file_name + file_suffix)
        project_secret_file = project_dir_path / (file_name + '.secret' + file_suffix)
        return anyconfig.multi_load([project_file, project_secret_file], ac_ignore_missing=True)

    @staticmethod
    def _get_workspace_options(options, workspace):
        """Returns the option values defined for the specific workspace or globally."""
        workspaces = options.pop('workspaces', {})
        workspace_options = {k: v for x in workspaces if x.pop('workspace', None) == workspace
                             for k, v in x.items()}
        return {**options, **workspace_options}

    def _get_service_options(self, services, service, workspace):
        """Returns the option values defined for the specific service and workspace or globally."""

        service_options = {}
        for s in services:
            if s.pop('service', None) == service:
                s.pop('module', None)
                service_options.update(self._get_workspace_options(s, workspace))
        return {**service_options}

    def get_module_options(self, options_list, module, service, workspace):
        """Returns the option values defined for the specific module, service and workspace or globally."""

        if type(options_list) is not list:
            options_list = [options_list]

        service_options = {}
        module_options = {}
        for options in options_list:
            if 'module' not in options or options.pop('module') == module:
                services = options.pop('services', {})
                module_options.update(self._get_workspace_options(options, workspace))
                service_options.update(self._get_service_options(services, service, workspace))

        return {**module_options, **service_options}


@dataclass
class ServiceConfig:
    project_config: ProjectConfig
    module: str
    service: str
    workspace: str

    @property
    def client_params(self):
        res = asdict(self)
        del res['project_config']
        res['project_dir'] = self.project_config.project_dir
        return res

    def get_command(self, cmd_name, ms):
        """Get the command associated to this microservice."""

        # Get command already added in handler
        for name in ms.commands:
            if name == cmd_name:
                return ms.commands[name]

        # Creates it from project class parameter if not already defined
        cmd_class = self._command_class(cmd_name)
        if cmd_class:
            cmd = cmd_class(ms, name=cmd_name)

            # Installs needed commands
            for needed in cmd.needed_commands:
                self.get_command(needed, ms)

            return cmd

    def _command_class(self, cmd_name):
        """Loads the command class defined by name."""
        cmd_class_name = self.get_command_options(cmd_name).get('class')
        if cmd_class_name:
            splitted = cmd_class_name.split('.')
            return import_attr('.'.join(splitted[:-1]), splitted[-1], cwd=self.project_config.project_dir)

    def get_command_options(self, cmd_name):
        options = deepcopy(self.project_config.all_commands.get(cmd_name, {}))
        module_options = self.project_config.get_module_options(options, self.module, self.service, self.workspace)
        return {**self.client_params, **module_options}


def main():
    return client()


if __name__ == "__main__":
    main()
