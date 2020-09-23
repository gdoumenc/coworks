import sys
from functools import partial

import anyconfig
import click

from coworks.config import DEFAULT_PROJECT_DIR, DEFAULT_WORKSPACE
from coworks.cws.error import CwsClientError
from coworks.utils import import_attr
from coworks.version import __version__

from .utils import get_system_info


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


def invoke(initial, ctx):
    """Invokes the command over the service or the declared services in project configuration file."""
    try:
        args = ctx.args
        protected_args = ctx.protected_args

        cmd_name = protected_args[0] if protected_args else None

        project_dir = ctx.params.get('project_dir')
        module = ctx.params.get('module')
        service = ctx.params.get('service')
        workspace = ctx.params.get('workspace')

        project_config = ProjectConfig(cmd_name, project_dir)
        if service:
            services = [(module, service)]
        else:
            services = project_config.services

        # Iterates over the declared services in project configuration file
        for module, service in services:
            ctx.args = list(args)
            ctx.protected_args = protected_args

            # Get command from the microservice
            cmd_project_config = ProjectConfig(cmd_name, project_dir)
            handler = get_handler(project_dir, module, service)
            cmd = project_config.get_command(handler, module, service, workspace)
            if not cmd:
                raise CwsClientError(f"Undefined command {cmd_name}.\n")

            # Get user defined options and convert them in right types
            client_opts, _, cmd_opts = cmd.make_parser(ctx).parse_args(ctx.args)
            for opt_key, opt_value in client_opts.items():
                cmd_opt = next(x for x in cmd_opts if x.name == opt_key)
                client_opts[opt_key] = cmd_opt.type(opt_value)

            client_params = {'project_dir': project_dir, 'module': module, 'service': service, 'workspace': workspace}
            complemented_args = cmd_project_config.missing_options(**client_params, **client_opts)
            cmd.execute(**client_params, **complemented_args)
    except CwsClientError as client_err:
        sys.stderr.write(client_err.msg)
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e))
        sys.exit(1)


client.invoke = partial(invoke, client.invoke)


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


class ProjectConfig:
    """Class for the project configuration file for commands."""

    def __init__(self, cmd_name, project_dir):
        from pathlib import Path
        self.cmd_name = cmd_name
        self.project_dir = project_dir
        self.params = {}
        self.__all_command_options = self.__all_default_options = None

        project_file = Path(self.project_dir) / "cws.project.yml"
        project_secret_file = Path(self.project_dir) / "cws.project.secret.yml"
        self.params = anyconfig.multi_load([project_file, project_secret_file], ac_ignore_missing=True)

    def get_command(self, ms, module, service, workspace):
        """Get the command associated to this microservice."""

        # Get command in handler
        for name in ms.commands:
            if name == self.cmd_name:
                return ms.commands[name]

        # Creates it from project class parameter if not already defined
        cmd_class = self.__command_class(module, service, workspace)
        if cmd_class:
            cmd = cmd_class(ms, name=self.cmd_name)

            # Installs needed commands
            for needed in cmd.needed_commands:
                proj = ProjectConfig(needed, self.project_dir)
                proj.get_command(ms, module, service, workspace)

            click.help_option()(cmd)
            return cmd

    def missing_options(self, project_dir, module, service, workspace, **options):
        """Adds project options to the command options."""
        for key in self._all_options_keys(module, service, workspace):
            if key == 'class':
                continue
            if key not in options or options[key] is None:
                options[key] = self._get_option(module, service, workspace, key)
        return options

    @property
    def services(self):
        """ Returns the list of microservices on which the command will be executed."""
        services = self.params.get('services')
        if not services:
            raise CwsClientError("No service defined in project file\n")
        return [(s['module'], s['service']) for s in services]

    def _get_option(self, module, service, workspace, key):
        default_options = self.all_default_options
        service_options = self._service_options(module, service, workspace)
        if key in service_options:
            return service_options[key]
        elif key in default_options:
            return default_options[key]

    @property
    def all_command_options(self):
        if self.__all_command_options is None:
            cmd_name = self.cmd_name
            self.__all_command_options = self.params.get('commands', {}).get(cmd_name, {})

            # verify configuration structure
            for s in self.__all_command_options.get('services', []):
                if 'module' not in s:
                    raise CwsClientError(f"The command {cmd_name} has options defined without module declaration\n")

        return self.__all_command_options

    @property
    def all_default_options(self):
        """Default descriptioin in project file."""
        if self.__all_default_options is None:
            self.__all_default_options = self.all_command_options.get('default', {})
        return self.__all_default_options

    def _service_options(self, module, service, workspace):
        services = [s for s in self.all_command_options.get('services', []) if
                    (s.get('module') == module and 'service' not in s)
                    or (s.get('module') == module and s.get('service') == service)]

        workspace_defined_services = [s for s in services if s.get('workspace') == workspace]
        workspace_undefined_services = [s for s in services if 'workspace' not in s]

        if workspace_defined_services:
            options = {**workspace_defined_services[0]}
        elif workspace_undefined_services:
            options = {**workspace_undefined_services[0]}
        else:
            options = {}
        options.pop('module', None)
        options.pop('service', None)
        options.pop('workspace', None)
        return options

    def _all_options_keys(self, module, service, workspace):
        return self.all_default_options.keys() | self._service_options(module, service, workspace).keys()

    def __command_class(self, module, service, workspace):
        cmd_class_name = self._get_option(module, service, workspace, 'class')
        if cmd_class_name:
            splitted = cmd_class_name.split('.')
            return import_attr('.'.join(splitted[:-1]), splitted[-1], cwd=self.project_dir)


if __name__ == "__main__":
    main()
