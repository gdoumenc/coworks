import sys
from functools import partial
from pathlib import Path

import anyconfig
import click
from chalice.cli import chalice_version, get_system_info

from coworks.config import DEFAULT_PROJECT_DIR, DEFAULT_WORKSPACE
from coworks.utils import import_attr
from coworks.version import __version__


class CLIError(Exception):
    def __init__(self, message):
        self.msg = message


@click.group()
@click.version_option(version=__version__,
                      message=f'%(prog)s %(version)s, chalice {chalice_version}, {get_system_info()}')
@click.option('-p', '--project-dir', default=DEFAULT_PROJECT_DIR,
              help='The project directory path (absolute or relative). Defaults to CWD')
@click.option('-m', '--module', help="Filename of your microservice python source file.")
@click.option('-s', '--service', help="Coworks application in the source file.")
@click.option('-w', '--workspace', default=DEFAULT_WORKSPACE, help="Application stage.")
@click.pass_context
def client(*args, **kwargs):
    ...


def invoke(initial, ctx):
    try:
        cmd_name = ctx.protected_args[0] if ctx.protected_args else None
        args = ctx.args
        protected_args = ctx.protected_args

        project_dir = ctx.params.get('project_dir')
        module = ctx.params.get('module')
        service = ctx.params.get('service')
        workspace = ctx.params.get('workspace')
        project_config = ProjectConfig(cmd_name, project_dir, module, service, workspace)

        for project_dir, module, service, workspace in project_config.services:
            handler = get_handler(project_dir, module, service)
            cmd = project_config.get_command(handler)
            execute_command(cmd, module, service, workspace, project_config)
            initial(ctx)
            ctx.args = args
            ctx.protected_args = protected_args
    except CLIError as client_err:
        sys.stderr.write(client_err.msg)
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e))
        sys.exit(1)


client.invoke = partial(invoke, client.invoke)


def main():
    return client(obj={})


def get_handler(project_dir, module, service):
    # Load handler
    try:
        return import_attr(module, service, cwd=project_dir)
    except AttributeError as e:
        raise CLIError(f"Module '{module}' has no microservice {service} : {str(e)}\n")
    except ModuleNotFoundError as e:
        raise CLIError(f"The module '{module}' is not defined in {project_dir} : {str(e)}\n")
    except Exception as e:
        raise CLIError(f"Error {e} when loading module '{module}'\n")


def execute_command(cmd, module, service, workspace, project_config):
    def call_execute(**command_options):
        try:
            cmd.execute(**project_config.get_options(command_options, module, service, workspace))
        except Exception as err:
            raise CLIError(str(err))

    if not cmd:
        raise CLIError(f"Undefined command {cmd}.\n")

    f = call_execute
    for opt in cmd.options:
        f = opt(f)
    return client.command(project_config.cmd_name)(f)


class ProjectConfig:
    def __init__(self, cmd_name, project_dir, module, service, workspace, project_file="cws.project.yml"):
        self.cmd_name = cmd_name
        self.project_dir = project_dir
        self.module = module
        self.service = service
        self.workspace = workspace
        self.params = {}
        self.__all_options = self.__default_options = None

        project_file = Path(self.project_dir) / project_file
        if project_file.is_file():
            with project_file.open('r') as file:
                self.params = anyconfig.load(file)

    def get_command(self, app):
        # Get command in handler
        for name in app.commands:
            if name == self.cmd_name:
                return app.commands[name]

        # Creates it from project class parameter if doesn't exist
        if self.cmd_name not in app.commands:
            cmd_class = self.__command_class()
            if cmd_class:
                return cmd_class(app, name=self.cmd_name)

    def get_options(self, command_options, module, service, workspace):
        """Adds project options to the command options."""
        options = {
            'project_dir': self.project_dir,
            'module': self.module,
            'service': self.service,
            'workspace': self.workspace,
        }
        for key in self._all_options_keys(module, service) | command_options.keys():
            if key in command_options and command_options[key] is not None:
                options[key] = command_options[key]
            else:
                options[key] = self._get_option(module, service, workspace, key)
        return options

    @property
    def services(self):
        """ Returns the list of microservices on which the command will be executed."""
        if self.service is None:
            services = self.params.get('services') if self.module is None else None
            if not services:
                raise CLIError("No service defined in project file\n")
            return [(self.project_dir, s['module'], s['service'], self.workspace) for s in services]
        return [(self.project_dir, self.module, self.service, self.workspace)]

    def _get_option(self, module, service, workspace, key):
        default_options = self._default_options
        service_options = self._service_options(module, service)
        if key in service_options:
            return service_options[key]
        elif key in default_options:
            return default_options[key]

    def __command_class(self):
        cmd_class_name = self._get_option(self.module, self.service, self.workspace, 'class')
        if cmd_class_name:
            splitted = cmd_class_name.split('.')
            return import_attr('.'.join(splitted[:-1]), splitted[-1], cwd=self.project_dir)

    @property
    def _all_options(self):
        if self.__all_options is None:
            self.__all_options = self.params.get('commands', {}).get(self.cmd_name, {})
        return self.__all_options

    @property
    def _default_options(self):
        if self.__default_options is None:
            self.__default_options = self._all_options.get('default', {})
        return self.__default_options

    def _service_options(self, module, service):
        services = [s for s in self._all_options.get('services', []) if
                    s.get('module') == module and s.get('service') == service]
        options = {**services[0]} if services else {}
        options.pop('module', None)
        options.pop('service', None)
        return options

    def _all_options_keys(self, module, service):
        return self._default_options.keys() | self._service_options(module, service).keys()


if __name__ == "__main__":
    main()
