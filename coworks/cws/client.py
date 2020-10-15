import sys
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, asdict
from logging import getLogger, WARNING

import anyconfig
import click

from .error import CwsClientError
from ..config import DEFAULT_PROJECT_DIR, DEFAULT_WORKSPACE
from ..utils import import_attr, get_system_info
from ..version import __version__


@click.group()
@click.version_option(version=__version__, message=f'%(prog)s %(version)s, {get_system_info()}')
@click.option('-p', '--project-dir', default=DEFAULT_PROJECT_DIR,
              help='The project directory path (absolute or relative). Defaults to CWD')
@click.option('-m', '--module', help="Filename of your microservice python source file.")
@click.option('-s', '--service', help="Coworks application in the source file.")
@click.option('-w', '--workspace', default=DEFAULT_WORKSPACE, help="Application stage.")
@click.pass_context
def client(*args, **kwargs):
    ...


def invoke(ctx):
    """Invokes the command over the service or the declared services in project configuration file."""
    try:
        args = ctx.args
        protected_args = ctx.protected_args

        command_name = protected_args[0] if protected_args else None

        project_dir = ctx.params.get('project_dir')
        workspace = ctx.params.get('workspace')
        module = ctx.params.get('module')
        service = ctx.params.get('service')

        project_config = ProjectConfig(project_dir)
        if service:
            services = [(module, service)]
        else:
            services = project_config.all_services(module)

        if not services:
            sys.stderr.write(str("Nothing to execute as no service defined."))
            sys.exit(1)

        # Iterates over the declared services in project configuration file
        commands_to_be_executed = defaultdict(list)
        for module, service in services:
            ctx.args = list(args)
            ctx.protected_args = protected_args
            service_config = project_config.get_service_config(module, service, workspace)

            # Get command from the microservice
            handler = get_handler(project_dir, module, service)
            command = service_config.get_command(command_name, handler)
            if not command:
                raise CwsClientError(f"Undefined command {command_name}.\n")
            command_options = service_config.get_command_options(command_name)

            # Get user defined options and convert them in right types
            client_options, _, cmd_opts = command.make_parser(ctx).parse_args(ctx.args)
            for opt_key, opt_value in client_options.items():
                cmd_opt = next(x for x in cmd_opts if x.name == opt_key)
                client_options[opt_key] = cmd_opt.type(opt_value)

            execution_params = {**command_options, **client_options}
            command.make_context(command.name, execution_params)
            commands_to_be_executed[type(command)].append((command, execution_params))
        for command_class, execution_params in commands_to_be_executed.items():
            command_class.multi_execute(project_dir, workspace, execution_params)
    except CwsClientError as client_err:
        sys.stderr.write(client_err.msg)
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e))
        sys.exit(1)


client.invoke = invoke


class ProjectConfig:
    """Class for the project configuration file."""

    def __init__(self, project_dir, file_name="cws.project", file_suffix=".yml"):
        from pathlib import Path
        self.project_dir = project_dir
        self.params = {}

        project_dir_path = Path(project_dir)
        self.project_file = project_dir_path / (file_name + file_suffix)
        project_secret_file = project_dir_path / (file_name + '.secret' + file_suffix)
        getLogger('anyconfig').setLevel(WARNING)
        self.params = anyconfig.multi_load([self.project_file, project_secret_file], ac_ignore_missing=True)

    def get_service_config(self, module, service, workspace):
        return ServiceConfig(self, module, service, workspace)

    def all_services(self, module=None):
        """ Returns the list of microservices on which the command will be executed."""
        services = self.params.get('services', {})

        res = []
        for s in services:
            if 'module' not in s:
                continue

            if module and s['module'] != module:
                continue

            if 'service' in s:
                res.append((s['module'], s['service']))
            elif 'services' in s:
                for ss in s['services']:
                    if 'service' in ss:
                        res.append((s['module'], ss['service']))
        return res

    @property
    def all_commands(self):
        """ Returns the list of microservices on which the command will be executed."""
        return self.params.get('commands', {})

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

            click.help_option()(cmd)
            return cmd

    def _command_class(self, cmd_name):
        cmd_class_name = self.get_command_options(cmd_name).get('class')
        if cmd_class_name:
            splitted = cmd_class_name.split('.')
            return import_attr('.'.join(splitted[:-1]), splitted[-1], cwd=self.project_config.project_dir)

    def get_command_options(self, cmd_name):
        options = deepcopy(self.project_config.all_commands.get(cmd_name, {}))
        module_options = self.project_config.get_module_options(options, self.module, self.service, self.workspace)
        return {**self.client_params, **module_options}


def main():
    return client(obj={})


def get_handler(project_dir, module, service):
    # Load microservice handler
    try:
        return import_attr(module, service, cwd=project_dir)
    except AttributeError as e:
        raise CwsClientError(f"Module '{module}' has no microservice {service} : {str(e)}\n")
    except ModuleNotFoundError as e:
        raise CwsClientError(f"The module '{module}' is not defined in {project_dir} : {str(e)}\n")
    except Exception as e:
        raise CwsClientError(f"Error {e} when loading module '{module}'\n")


if __name__ == "__main__":
    main()
