import os
from python_terraform import Terraform

import click

from .command import CwsCommand


class CwsDeployer(CwsCommand):
    def __init__(self, app=None):
        super().__init__(app, name='deploy')

    @property
    def options(self):
        return (
            click.option('-w', '--workspace', default='dev'),
            click.option('--debug/--no-debug', default=False, help='Print debug logs to stderr.')
        )

    def _execute(self, *, workspace, project_dir='.', debug=True, **kwargs):
        print(self.app.config)
        print("deploy")

    def _local_deploy(self, deploy_config, workspace, debug):
        print("deploy")

        if debug:
            print("Local deployment")

        try:
            deploy_config = deploy_config['deploy']
        except KeyError:
            raise Exception("Configuration file does not contain section 'deploy'")

        try:
            services_config = deploy_config['services']
        except KeyError:
            raise Exception("Configuration file does not contain section 'services' in the section 'deploy'")

        services_to_deploy_config = [service_config for service_config in services_config if
                                     service_config['workspace'] == workspace]

        if debug:
            print(f"Preparing to deploy the following services : {services_to_deploy_config}")

        for service_to_deploy_config in services_to_deploy_config:

            terraform_variables = {'environment_variables_file': service_to_deploy_config['environment_variables_file'],
                                   'custom-layers': service_to_deploy_config.get('custom-layers'),
                                   'common-layers': service_to_deploy_config.get('common-layers'),
                                   'stage': ''}

            if debug:
                print("Create terraform configuration")
            t = Terraform(working_dir=os.path.join('.', deploy_config['terraform']))

            if debug:
                print("Deploying")

            t.workspace('select', 'default')
            t.init(input=False)
            return_code, stdout, stderr = t.apply(skip_plan=True, input=False, var=terraform_variables)
            if debug:
                print(return_code, stdout, stderr)

            return_code, stdout, stderr = t.workspace('select', service_to_deploy_config['workspace'])
            if return_code != 0:
                t.workspace('new', service_to_deploy_config['workspace'])
            t.init(input=False)
            return_code, stdout, stderr = t.apply(skip_plan=True, input=False, var=terraform_variables)
            if debug:
                print(return_code, stdout, stderr)

            terraform_variables['stage'] = service_to_deploy_config['workspace']

            t.workspace('select', 'default')
            return_code, stdout, stderr = t.apply(skip_plan=True, input=False, var=terraform_variables)
            if debug:
                print(return_code, stdout, stderr)

            return_code, stdout, stderr = t.workspace('select', service_to_deploy_config['workspace'])
            if return_code != 0:
                t.workspace('new', service_to_deploy_config['workspace'])
            return_code, stdout, stderr = t.apply(skip_plan=True, input=False, var=terraform_variables)
            if debug:
                print(return_code, stdout, stderr)