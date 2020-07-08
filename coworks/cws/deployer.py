import os

import click
from python_terraform import Terraform

from .command import CwsCommand


class CwsDeployer(CwsCommand):
    def __init__(self, app=None, name='deploy'):
        super().__init__(app, name=name)

    @property
    def options(self):
        return (
            click.option('--dry', is_flag=True, help="Doesn't perform terraform commands."),
            click.option('--remote', '-r', is_flag=True, help="Deploy on fpr-coworks.io."),
            click.option('--debug/--no-debug', default=False, help="Print debug logs to stderr."),
        )

    def _execute(self, options):
        if options['remote']:
            self._remote_deploy(options)
        else:
            self._local_deploy(options)

    def _remote_deploy(self, options):
        pass

    def _local_deploy(self, options):
        terraform = Terraform(working_dir=os.path.join('.', 'terraform'))
        self._terraform_export_and_apply_local(terraform, options)
        self._terraform_export_and_apply_local(terraform, options)

    def _terraform_export_and_apply_local(self, terraform, options):
        output_file = os.path.join(".", "terraform", f"_{options.module}-{options.service}.tf")
        self.app.execute('terraform-staging', output=output_file, **options.to_dict())

        if not options['dry']:
            debug = options['debug']
            terraform_apply_local(terraform, "default", debug)
            terraform_apply_local(terraform, options.workspace, debug)


def terraform_apply_local(terraform, workspace, debug):
    return_code, stdout, stderr = terraform.workspace('select', workspace)
    if workspace != 'default' and return_code != 0:
        terraform.workspace('new', workspace)
    terraform.init(input=False)
    return_code, stdout, stderr = terraform.apply(skip_plan=True, input=False)
    # return_code, stdout, stderr = terraform.plan(input=False)
    if debug:
        print(return_code, stdout, stderr)
