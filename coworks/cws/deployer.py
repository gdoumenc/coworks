import click
import os
import subprocess

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
        CwsDeployer._terraform_export_and_apply_local(terraform, project_dir, module, service, workspace, '', debug)
        CwsDeployer._terraform_export_and_apply_local(terraform, project_dir, module, service, workspace, workspace, debug)

    @staticmethod
    def _terraform_export_and_apply_local(terraform, project_dir, module, service, workspace, stage, debug):
        tf_file_content = subprocess.check_output(
            f"cws -p {project_dir} -m {module} -s {service} terraform-staging --stage={stage} --workspace={workspace}",
            shell=True).decode('utf-8')
        with open(os.path.join(".", "terraform", f"_{module}-{service}.tf"), 'w') as tf_file:
            tf_file.write(tf_file_content)
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
