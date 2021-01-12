import click

from .command import CwsCommand, CwsCommandError


class CwsInformant(CwsCommand):
    """Command to get information on the project's microservices and teir deployment."""

    @classmethod
    def multi_execute(cls, project_dir, workspace, client_options, execution_context):
        for command, command_options in execution_context:
            command.print_module_info(**command_options)
            if command_options['env']:
                command.print_env_vars(**command_options)

    def __init__(self, app=None, name='info'):
        super().__init__(app, name=name)

    @property
    def options(self):
        return [
            *super().options,
            click.option('--env', '-e', is_flag=True, help="Show environment variables."),
        ]

    def _execute(self, *, workspace, **options):
        raise CwsCommandError("Not implemented")

    def print_module_info(self, *, module, service, **options):
        print(f"Microservice {service} defined in module {module}")

    def print_env_vars(self, *, project_dir, workspace, service, **options):
        for config in self.app.configs:
            if config.workspace == workspace:
                print(f"Environment vars for {service} in workspace {config.workspace}:")
                files = config.existing_environment_variables_files(project_dir)
                for file in files:
                    with file.open() as f:
                        print(f.read())
