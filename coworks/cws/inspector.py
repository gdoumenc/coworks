import click

from .command import CwsCommand, CwsCommandError
from .. import aws


class CwsInspector(CwsCommand):
    """Command to get information on a microservice."""

    @classmethod
    def multi_execute(cls, project_dir, workspace, execution_list):
        for command, command_options in execution_list:
            command.print_module_info(**command_options)
            if command_options['env']:
                command.print_env_vars(**command_options)

    def __init__(self, app=None, name='inspect'):
        super().__init__(app, name=name)

    @property
    def options(self):
        return [
            *super().options,
            click.option('--env', '-e', is_flag=True, help="Show environment variables."),
        ]

    def print_module_info(self, *, module, service, **options):
        print(f"Microservice {service} defined in module {module}")

    def print_env_vars(self, *, project_dir, workspace, service, **options):
        for config in self.app.configs:
            if config.is_valid_for(workspace):
                print(f"Environment vars for {service} in workspace {config.workspace}:")
                files = config.existing_environment_variables_files(project_dir)
                for file in files:
                    with file.open() as f:
                        print(f.read())


class CwsAWSInspector(CwsCommand):
    """Command to get information on the project's microservices and teir deployment."""

    @classmethod
    def multi_execute(cls, project_dir, workspace, execution_list):
        for command, command_options in execution_list:
            profile_name = command_options['profile_name']
            aws_api_session = aws.ApiGatewaySession(profile_name=profile_name)
            paginator = aws_api_session.client.get_paginator('get_rest_apis')
            apis = command.get_apis(command.app.name, paginator)
            for api in apis:
                print(command.get_result(api))

    def __init__(self, app=None, name='deployed'):
        super().__init__(app, name=name)

    @property
    def options(self):
        return [
            *super().options,
            click.option('--profile-name', '-p', required=True, help="AWS profile for APIGateway access."),
            click.option('--env', '-e', is_flag=True, help="Show environment variables."),
        ]

    def get_apis(self, service_name, paginator, page_size=10):
        rest_apis = paginator.paginate(PaginationConfig={'PageSize': page_size})
        return rest_apis.search(f"items[?starts_with(name, '{service_name}')]")

    def get_result(self, api):
        return {
            'name': api['name'],
            'id': api['id'],
        }
