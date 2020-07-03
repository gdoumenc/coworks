import click
import os
import subprocess

from coworks.cws.client import client
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
        CwsDeployer._local_deploy(workspace, debug, project_dir, **kwargs)

    @staticmethod
    def _local_deploy(workspace, debug, project_dir, module=None, service=None, **kwargs):
        from python_terraform import Terraform
        terraform = Terraform(working_dir=os.path.join('.', 'terraform'))
        CwsDeployer._terraform_export_and_apply_local(terraform, project_dir, module, service, workspace, 'create',
                                                      debug)
        CwsDeployer._terraform_export_and_apply_local(terraform, project_dir, module, service, workspace, 'update',
                                                      debug)

    @staticmethod
    def _terraform_export_and_apply_local(terraform, project_dir, module, service, workspace, step, debug):
        try:
            client(prog_name='cws',
                   args=['-p', project_dir, '-m', module, '-s', service, 'terraform-staging', '--step',
                         step, '--workspace', workspace, '--output',
                         os.path.join(".", "terraform", f"_{module}-{service}.tf")], obj={})
        except SystemExit:
            pass  # ignoring system exit after calling client

        CwsDeployer._terraform_apply_local(terraform, "default", debug)
        CwsDeployer._terraform_apply_local(terraform, workspace, debug)

    @staticmethod
    def _terraform_apply_local(terraform, workspace, debug):
        return_code, stdout, stderr = terraform.workspace('select', workspace)
        if workspace != 'default' and return_code != 0:
            terraform.workspace('new', workspace)
        terraform.init(input=False)
        return_code, stdout, stderr = terraform.apply(skip_plan=True, input=False)
        # return_code, stdout, stderr = terraform.plan(input=False)
        if debug:
            print(return_code, stdout, stderr)
