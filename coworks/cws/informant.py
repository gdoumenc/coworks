from pathlib import Path

import click
from python_terraform import Terraform

from coworks.cws.command import CwsCommand, CwsCommandError


class CwsInformant(CwsCommand):
    """Command to get information on the project's microservices and teir deployment."""

    @classmethod
    def multi_execute(cls, project_dir, workspace, execution_params):
        terraform, tf_dir = False, ''
        for command, options in execution_params:
            command.print_module_info(**options)

            terraform, tf_dir = options['terraform'], options['tf_dir']

            if options['env']:
                command.print_env_vars(**options)

        if terraform:
            cls.print_terraform_output(tf_dir)

    def __init__(self, app=None, name='info'):
        super().__init__(app, name=name)

    @property
    def options(self):
        return [
            *super().options,
            click.option('--env', '-e', is_flag=True, help="Show environment variables."),
            click.option('--terraform', '-t', is_flag=True, help="Show deployed terraform output."),
            click.option('--tf_dir', default='terraform', help="Terraform directory."),
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

    @classmethod
    def print_terraform_output(cls, tf_dir):
        if Path(tf_dir).exists():
            terraform = Terraform(tf_dir)
            print(terraform.output())
