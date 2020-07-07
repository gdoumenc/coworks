import os

import click

from .command import CwsCommand


class CwsDeployer(CwsCommand):
    def __init__(self, app=None, name='deploy'):
        super().__init__(app, name=name)

    @property
    def options(self):
        return (
            click.option('--debug/--no-debug', default=False, help='Print debug logs to stderr.'),
        )

    def _execute(self, *, workspace, project_dir='.', debug=True, **kwargs):
        self._local_deploy(workspace, debug, project_dir, **kwargs)

    def _local_deploy(self, workspace, debug, project_dir, module=None, service=None, **kwargs):
        from python_terraform import Terraform
        terraform = Terraform(working_dir=os.path.join('.', 'terraform'))
        self._terraform_export_and_apply_local(terraform, project_dir, module, service, workspace, 'create', debug)
        self._terraform_export_and_apply_local(terraform, project_dir, module, service, workspace, 'update', debug)

    def _terraform_export_and_apply_local(self, terraform, project_dir, module, service, workspace, step, debug):
        self.app.execute('terraform-staging', project_dir=project_dir, module=module, service=service,
                         workspace=workspace, step=step, debug=debug,
                         output=os.path.join(".", "terraform", f"_{module}-{service}.tf"))
        self._terraform_apply_local(terraform, "default", debug)
        self._terraform_apply_local(terraform, workspace, debug)

    def _terraform_apply_local(self, terraform, workspace, debug):
        return_code, stdout, stderr = terraform.workspace('select', workspace)
        if workspace != 'default' and return_code != 0:
            terraform.workspace('new', workspace)
        terraform.init(input=False)
        return_code, stdout, stderr = terraform.apply(skip_plan=True, input=False)
        # return_code, stdout, stderr = terraform.plan(input=False)
        if debug:
            print(return_code, stdout, stderr)
