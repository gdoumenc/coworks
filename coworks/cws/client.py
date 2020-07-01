import sys
from functools import partial
from pathlib import Path

import anyconfig
import click
from chalice.cli import chalice_version, get_system_info

from coworks.utils import import_attr
from coworks.version import __version__


class CLIError(Exception):
    def __init__(self, message):
        self.msg = message


@click.group()
@click.version_option(version=__version__,
                      message=f'%(prog)s %(version)s, chalice {chalice_version}, {get_system_info()}')
@click.option('-p', '--project-dir', default='.',
              help='The project directory path (absolute or relative). Defaults to CWD')
@click.option('-m', '--module', help="Filename of your microservice python source file.")
@click.option('-s', '--service', help="Coworks application in the source file.")
@click.pass_context
def client(*args, **kwargs):
    ...


def invoke(initial, ctx):
    try:
        cmd_name = ctx.protected_args[0] if ctx.protected_args else None
        args = ctx.args
        protected_args = ctx.protected_args
        project_config = ProjectConfig(cmd_name, ctx.params)
        for module, service, project_dir in project_config.services:
            execute_command(project_dir, module, service, project_config)
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


def execute_command(project_dir, module, service, config):
    # Load handler
    try:
        handler = import_attr(module, service, cwd=project_dir)
    except AttributeError as e:
        raise CLIError(f"Module '{module}' has no microservice {service} : {str(e)}\n")
    except ModuleNotFoundError as e:
        raise CLIError(f"The module '{module}' is not defined in {project_dir} : {str(e)}\n")
    except Exception as e:
        raise CLIError(f"Error {e} when loading module '{module}'\n")

    # Get command in handler
    cmd = None
    for name in handler.commands:
        if name == config.cmd_name:
            cmd = handler.commands[name]

    # Creates it from project class parameter if doesn't exist
    if config.cmd_name not in handler.commands:
        cmd_class = config.command_class(module, service)
        if cmd_class:
            cmd = cmd_class(handler, name=config.cmd_name)

    # Executes the command with options
    if cmd:
        def call_execute(**command_options):
            try:
                cmd.execute(**config.get_options(command_options, module, service))
            except Exception as err:
                raise CLIError(str(err))

        f = call_execute
        for opt in cmd.options:
            f = opt(f)
        return client.command(config.cmd_name)(f)


class ProjectConfig:
    def __init__(self, cmd_name, params, project_file="cws.project.yml"):
        self.cmd_name = cmd_name
        self.project_dir = params.get('project_dir')
        self.module = params.get('module')
        self.service = params.get('service')
        self.__all_options = self.__default_options = None

        project_file = Path(self.project_dir) / project_file
        if project_file.is_file():
            with project_file.open('r') as file:
                self.params = anyconfig.load(file)

    def get_options(self, command_options, module, service):
        options = {
            'project_dir': self.project_dir,
            'module': self.module,
            'service': self.service,
        }

        for key in self.default_options.keys() | \
                   self.service_options(module, service).keys() | command_options.keys():
            if key in command_options and command_options[key] is not None:
                options[key] = command_options[key]
            elif key in self.service_options(module, service):
                options[key] = self.service_options(module, service)[key]
            elif key in self.default_options:
                options[key] = self.default_options[key]
            else:
                options[key] = None
        return options

    @property
    def services(self):
        """ Returns the list of microservices on which the command will be executed."""
        if self.service is None:
            services = self.params.get('services') if self.module is None else None
            if not services:
                raise CLIError("No service defined in project file\n")
            return [(s['module'], s['service'], self.project_dir) for s in services]
        return [(self.module, self.service, self.project_dir)]

    def get_value(self, module, service, key):
        default_options = self.default_options
        service_options = self.service_options(module, service)
        if key in service_options:
            return service_options[key]
        elif key in default_options:
            return default_options[key]

    def command_class(self, module, service):
        cmd_class_name = self.get_value(module, service, 'class')
        if cmd_class_name:
            splitted = cmd_class_name.split('.')
            return import_attr('.'.join(splitted[:-1]), splitted[-1], cwd=self.project_dir)

    @property
    def all_options(self):
        if self.__all_options is None:
            self.__all_options = self.params.get('commands', {}).get(self.cmd_name, {})
        return self.__all_options

    @property
    def default_options(self):
        if self.__default_options is None:
            self.__default_options = self.all_options.get('default', {})
        return self.__default_options

    def service_options(self, module, service):
        services = [s for s in self.all_options.get('services', []) if
                    s.get('module') == module and s.get('service') == service]
        options = {**services[0]} if services else {}
        options.pop('module', None)
        options.pop('service', None)
        return options


if __name__ == "__main__":
    main()
