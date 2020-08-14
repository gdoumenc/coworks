from pathlib import Path
from pprint import PrettyPrinter
from threading import Thread

import click
import sys
from python_terraform import Terraform
from time import sleep

from .command import CwsCommand
from coworks import BizFactory


class CwsTerraform(Terraform):

    def __init__(self, working_dir, debug):
        super().__init__(working_dir=working_dir, terraform_bin_path='terraform')
        self.debug = debug
        self.__initialized = False

    def apply_local(self, workspace):
        self.select_workspace(workspace)
        if not self.__initialized:
            self.init()
            self.__initialized = True
        self.apply()

    def destroy_local(self, workspace):
        self.select_workspace(workspace)
        if not self.__initialized:
            self.init()
            self.__initialized = True
        self.destroy()

    def select_workspace(self, workspace):
        return_code, out, err = self.workspace('select', workspace)
        self._print(out, err)
        if workspace != 'default' and return_code != 0:
            return_code, out, err = self.workspace('new', workspace)
            self._print(out, err)

    def init(self, **kwargs):
        return_code, out, err = super().init(input=False, raise_on_error=True)
        self._print(out, err)

    def apply(self, **kwargs):
        return_code, out, err = super().apply(skip_plan=True, input=False, raise_on_error=True, parallelism=1)
        self._print(out, err)

    def destroy(self, **kwargs):
        return_code, out, err = super().destroy(input=False, raise_on_error=True)
        self._print(out, err)

    def output(self, *args, **kwargs):
        out = super().output(raise_on_error=True)
        pp = PrettyPrinter(compact=True)
        pp.pprint(out)

    def _print(self, out, err):
        if self.debug:
            print(out, file=sys.stdout)
            print(err, file=sys.stderr)


class CwsDeployer(CwsCommand):
    def __init__(self, app=None, name='deploy'):
        super().__init__(app, name=name)

    @property
    def needed_commands(self):
        return ['zip', 'terraform-staging']

    @property
    def options(self):
        return [
            *super().options,
            click.option('--dry', is_flag=True, help="Doesn't perform terraform commands."),
            click.option('--remote', '-r', is_flag=True, help="Deploy on fpr-coworks.io."),
            click.option('--debug/--no-debug', default=False, help="Print debug logs to stderr."),
        ]

    def _execute(self, options):
        if options['remote']:
            self._remote_deploy(options)
        else:
            self._local_deploy(options)

    def _remote_deploy(self, options):
        pass

    def _local_deploy(self, options):
        if isinstance(self.app, BizFactory):
            self.local_sfn_deploy(options)
        else:
            self.local_techms_deploy(options)

    def local_techms_deploy(self, options):
        """ Deploiement in 4 steps:
        create
            Step 1. Create API (destroys API integrations made in previous deployment)
            Step 2. Create Lambda (destroys API deployment made in previous deployment)
        update
            Step 3. Update API integrations
            Step 4. Update API deployment
        """
        print(f"Start deploying microservice {options.module}-{options.service}")
        options.pop('step')
        (Path('.') / 'terraform').mkdir(exist_ok=True)
        output_path = str(Path('.') / 'terraform' / f"_{options.module}-{options.service}.tf")

        if not options['dry']:
            print(f"Uploading zip of the microservice {options.module}-{options.service} to S3")
            self.app.execute('zip', **options.to_dict())

        if not options['dry']:
            print(f"Creating lambda and api resources for {options.module}-{options.service}...")
            terraform_thread = Thread(target=self._terraform_export_and_apply_local,
                                      args=('create', output_path, options))
            terraform_thread.start()
            CwsDeployer.display_spinning_cursor(terraform_thread)
            terraform_thread.join()

        if not options['dry']:
            print(f"Updating api integrations and deploying api for {options.module}-{options.service}...")
        terraform_thread = Thread(target=self._terraform_export_and_apply_local, args=('update', output_path, options))
        terraform_thread.start()
        CwsDeployer.display_spinning_cursor(terraform_thread)
        terraform_thread.join()

        if not options['dry']:
            print(f"Microservice {options.module}-{options.service} deployed in stage {options.workspace}.")
        else:
            print(f"Terraform {output_path} file created (dry mode).")

    def local_sfn_deploy(self, options):
        """ Deployment of step function in two steps :
        Step 1. Deploy API and lambda (that will be used to invoke the stepfunction) using the same deploy as for tech microservices
        Step 2. Deploy stepfunction :
            - 2.1. Translate stepfunction from yaml to json
            - 2.2 Export terraform for step function deployment
            - 2.3 Apply terraform
        """
        print("Stepfunction deployment :")

        # Step 1.
        biz_factory = self.app
        biz_factory_name = options['service']
        for biz_name, biz in self.app.biz.items():
            biz.deferred_init(options.workspace)
            self.app = biz
            options.__setitem__('service', biz_name)
            options.__setitem__('sfn_name', biz_factory_name)
            self.local_techms_deploy(options)
        self.app = biz_factory
        options.__setitem__('service', biz_factory_name)

        # Step 2.1
        (Path('.') / 'terraform').mkdir(exist_ok=True)
        output_path = str(Path('.') / 'terraform' / f"_{options.module}-{options.service}.json")
        self.app.execute('translate-sfn', output=output_path, **options.to_dict())

        # Step 2.2
        output_path = str(Path('.') / 'terraform' / f"_{options.module}-{options.service}-sfn.tf")
        self.app.execute('export-sfn', output=output_path, **options.to_dict())

        # Step 2.3
        terraform = CwsTerraform(Path('.') / 'terraform', options['debug'])
        terraform_thread = Thread(target=terraform.apply_local, args=(options['workspace'], ))
        terraform_thread.start()
        print("Creating step function resource ...")
        CwsDeployer.display_spinning_cursor(terraform_thread)
        terraform_thread.join()
        terraform.output()

    def _terraform_export_and_apply_local(self, step, output_path, options):
        self.app.execute('terraform-staging', output=output_path, step=step, **options.to_dict())
        if not options['dry']:
            terraform = CwsTerraform(Path('.') / 'terraform', options['debug'])
            terraform.apply_local("default")
            terraform.apply_local(options.workspace)
            if step == 'update':
                terraform.output()

    @staticmethod
    def spinning_cursor():
        while True:
            for cursor in '|/-\\':
                yield cursor

    @staticmethod
    def display_spinning_cursor(thread):
        spinner = CwsDeployer.spinning_cursor()
        while thread.is_alive():
            sys.stdout.write(next(spinner))
            sys.stdout.flush()
            sleep(0.1)
            sys.stdout.write('\b')


class CwsDestroyer(CwsCommand):

    def __init__(self, app=None, name='destroy'):
        super().__init__(app, name=name)

    @property
    def needed_commands(self):
        return ['terraform-staging']

    @property
    def options(self):
        return [
            *super().options,
            click.option('--dry', is_flag=True, help="Doesn't perform terraform commands."),
            click.option('--remote', '-r', is_flag=True, help="Deploy on fpr-coworks.io."),
            click.option('--debug/--no-debug', default=False, help="Print debug logs to stderr."),
        ]

    def _execute(self, options):
        print(f"Start destroying microservice {options.module}-{options.service}")
        if options['remote']:
            self._remote_destroy(options)
        else:
            self._local_destroy(options)

    def _remote_destroy(self, options):
        pass

    def _local_destroy(self, options):
        (Path('.') / 'terraform').mkdir(exist_ok=True)
        output_path = str(Path('.') / 'terraform' / f"_{options.module}-{options.service}.tf")
        self.app.execute('terraform-staging', output=output_path, step='create', **options.to_dict())
        terraform = CwsTerraform(Path('.') / 'terraform', options['debug'])

        if not options['dry']:
            if options['debug']:
                print("Destroying api deployment ...")
            terraform.apply_local(options.workspace)

            if options['debug']:
                print("Destroying api integrations ...")
            terraform.apply_local('default')

            if options['debug']:
                print("Destroying lambdas ...")
            terraform.destroy_local(options.workspace)

            if options['debug']:
                print("Destroying api resource ...")
            terraform.destroy_local('default')

        print(f"Destroy microservice {options.module}-{options.service} completed")
