import itertools
import logging
import sys
from abc import ABC
from dataclasses import dataclass
from pathlib import Path
from threading import Thread
from time import sleep
from typing import List, Optional

import boto3
import click

from coworks.aws import AwsS3Session
from coworks.coworks import Entry
from .command import CwsCommand, CwsCommandError
from .writer import CwsTemplateWriter
from .zip import CwsZipArchiver
from ..config import CORSConfig

UID_SEP = '_'

logging.getLogger("python_terraform").setLevel(logging.ERROR)


@dataclass
class TerraformResource:
    parent_uid: str
    path: str
    entries: List[Entry]
    cors: CORSConfig

    @property
    def uid(self):
        def remove_brackets(path):
            return f"{path.replace('{', '').replace('}', '')}"

        if self.path is None:
            return ''

        last = remove_brackets(self.path)
        return f"{self.parent_uid}{UID_SEP}{last}" if self.parent_uid else last

    @property
    def is_root(self):
        return self.path is None

    @property
    def parent_is_root(self):
        return self.parent_uid == ''

    def __repr__(self):
        return f"{self.uid}:{self.entries}"


class CwsTerraformCommand(CwsCommand, ABC):
    WRITER_CMD = 'export'

    @property
    def options(self):
        return [
            *super().options,
            click.option('--memory_size', default=128),
            click.option('--timeout', default=30),
        ]

    def __init__(self, app=None, **kwargs):
        self.writer_cmd = self.add_writer_command(app)
        super().__init__(app, **kwargs)

    def add_writer_command(self, app):
        """Default writer command added if not already defined."""
        return app.commands.get(self.WRITER_CMD) or CwsTemplateWriter(app)

    @classmethod
    def generate_terraform_files(cls, step, app, terraform, filename, msg, **options):
        debug = options['debug']
        profile_name = options['profile_name']
        aws_region = boto3.Session(profile_name=profile_name).region_name

        if debug:
            print(msg)
        output = str(Path(terraform.working_dir) / filename)
        app.execute(cls.WRITER_CMD, template=["terraform.j2"], output=output, aws_region=aws_region,
                    step=step, api_resources=cls.terraform_api_resources(app), **options)

    @classmethod
    def generate_terraform_resources_list_file(cls, app, terraform, filename, msg, **options):
        debug = options['debug']
        profile_name = options['profile_name']
        aws_region = boto3.Session(profile_name=profile_name).region_name
        if not aws_region:
            raise CwsCommandError("No region defined for this profile.")

        if debug:
            print(msg)
        output = Path(terraform.working_dir) / filename
        app.execute(cls.WRITER_CMD, template=["resources.j2"], output=str(output), aws_region=aws_region,
                    api_resources=cls.terraform_api_resources(app), **options)

        return cls.read_terraform_resources_list_file(terraform, filename, **options)

    @classmethod
    def read_terraform_resources_list_file(cls, terraform, filename, **options):
        output = Path(terraform.working_dir) / filename
        with output.open('r') as res_file:
            lines = res_file.readlines()[1:]
            return [line[:-1] for line in lines if line.rstrip()]

    @staticmethod
    def terraform_api_resources(app):
        """Returns the list of flatten path (prev, last, entry)."""
        resources = {}

        def add_entries(previous, last, entries: Optional[List[Entry]]):
            ter_entry = TerraformResource(previous, last, entries, app.config.cors)
            uid = ter_entry.uid
            if uid not in resources:
                resources[uid] = ter_entry
            if resources[uid].entries is None:
                resources[uid].entries = entries
            return uid

        for route, entries in app.entries.items():
            previous_uid = ''
            if route.startswith('/'):
                route = route[1:]
            splited_route = route.split('/')

            # special root case
            if splited_route == ['']:
                add_entries(None, None, entries)
                continue

            # creates intermediate resources
            last_path = splited_route[-1:][0]
            for prev in splited_route[:-1]:
                previous_uid = add_entries(previous_uid, prev, None)

            # set entry keys for last entry
            add_entries(previous_uid, last_path, entries)

        return resources


class CwsTerraformDeployer(CwsTerraformCommand):
    """ Deploiement in 4 steps:
    create
        Step 1. Create API in default workspace (destroys API integrations made in previous deployment)
        Step 2. Create Lambda in stage workspace (destroys API deployment made in previous deployment)
    update
        Step 3. Update API routes integrations
        Step 4. Update API deployment
    """

    ZIP_CMD = 'zip'

    @property
    def options(self):
        return [
            *super().options,
            *self.zip_cmd.options,
            click.option('--binary_media_types'),
            click.option('--create', '-c', is_flag=True, help="Stop on create step."),
            click.option('--dry', is_flag=True, help="Doesn't perform deploy [Global option only]."),
            click.option('--layers', '-l', multiple=True, help="Add layer (full arn: aws:lambda:...)"),
            click.option('--output', '-o', is_flag=True, help="Print terraform output values."),
            click.option('--python', '-p', type=click.Choice(['3.7', '3.8']), default='3.8',
                         help="Python version for the lambda."),
            click.option('--update', '-u', is_flag=True, help="Only update lambda code [Global option only]."),
        ]

    @classmethod
    def multi_execute(cls, project_dir, workspace, execution_list):
        terraform = Terraform()
        terraform.init()

        # Output, dry, create, stop and update are global options
        dry = create = update_lambda_only = False
        for command, options in execution_list:
            dry = options.pop('dry', False) or dry
            create = options.pop('create', False) or create
            update_lambda_only = options.pop('update', False) or update_lambda_only

            # Set default bucket key value
            options['key'] = options['key'] or f"{options.get('module')}-{command.app.name}/archive.zip"

            # Stop if only print output
            output = options.pop('output', False)
            if output:
                print(f"terraform output : {terraform.output()}")
                return

        # Transfert zip file to S3 (to be done on each service)
        for command, options in execution_list:
            print(f"Uploading zip to S3")
            module_name = options.pop('module_name')
            ignore = options.pop('ignore') or ['.*', 'terraform']
            options.pop('hash')
            command.app.execute(cls.ZIP_CMD, ignore=ignore, module_name=module_name, hash=True, **options)

        # Generates default provider
        # cls.generate_common_terraform_files()

        # Get all terraform resources
        terraform_api_ressources = []
        for command, options in execution_list:
            terraform_filename = f"{command.app.name}.{command.app.ms_type}.txt"
            msg = f"Generate resources list for {command.app.name}"
            res = cls.generate_terraform_resources_list_file(command.app, terraform, terraform_filename, msg, **options)
            terraform_api_ressources.extend(res)

        # Generates terraform files (create step)
        if not update_lambda_only:
            for command, options in execution_list:
                terraform_filename = f"{command.app.name}.{command.app.ms_type}.tf"
                msg = f"Generate terraform files for creating API and lambdas for {command.app.name}"
                cls.generate_terraform_files("create", command.app, terraform, terraform_filename, msg, dry=dry,
                                             **options)

            # Apply terraform if not dry (create API with null resources and lambda step)
            # or in case of only updating lambda code
            if not dry:
                msg = ["Create API", "Create lambda"] if create else ["Update API", "Update lambda"]
                cls.terraform_apply(terraform, workspace, terraform_api_ressources, msg)

        # Stop on create step if needed
        if create:
            return

        # Generates terraform files (update step)
        for command, options in execution_list:
            terraform_filename = f"{command.app.name}.{command.app.ms_type}.tf"
            msg = f"Generate terraform files for updating API routes and deploiement for {command.app.name}"
            cls.generate_terraform_files("update", command.app, terraform, terraform_filename, msg, dry=dry,
                                         **options)

        # Apply terraform if not dry (update API routes and deploy step)
        if not dry:
            msg = ["Update API routes", f"Deploy API {workspace}"]
            cls.terraform_apply(terraform, workspace, terraform_api_ressources, msg,
                                update_lambda_only=update_lambda_only)

        # Traces output
        print(f"terraform output : {terraform.output()}")

    def __init__(self, app=None, name='deploy'):
        self.zip_cmd = self.add_zip_command(app)
        super().__init__(app, name=name)

    def add_zip_command(self, app):
        """Default zip command added if not already defined."""
        return app.commands.get(self.ZIP_CMD) or CwsZipArchiver(app)

    @staticmethod
    def generate_common_terraform_files():
        with open('terraform/default_provider.tf', 'w') as output:
            print('provider "aws" {\nprofile = "fpr-customer"\nregion = "eu-west-1"\n}', file=output, flush=True)

    @staticmethod
    def terraform_apply(terraform, workspace, targets, traces, update_lambda_only=False):
        """In the default terraform workspace, we have the API.
        In the specific workspace, we have the corresponding stagging lambda.
        """
        stop = False

        def display_spinning_cursor():
            spinner = itertools.cycle('|/-\\')
            while not stop:
                sys.stdout.write(next(spinner))
                sys.stdout.write('\b')
                sys.stdout.flush()
                sleep(0.1)

        spin_thread = Thread(target=display_spinning_cursor)
        spin_thread.start()

        try:
            if not update_lambda_only:
                print(f"Terraform apply ({traces[0]})", flush=True)
                terraform.apply("default", targets)
            print(f"Terraform apply ({traces[1]})", flush=True)
            terraform.apply(workspace, targets)
        finally:
            stop = True


class CwsTerraformDestroyer(CwsTerraformCommand):

    @property
    def options(self):
        return [
            *super().options,
            click.option('--all', '-a', is_flag=True, help="Destroy on all workspaces."),
            click.option('--bucket', '-b', help="Bucket to remove sources zip file from.", required=True),
            click.option('--debug', is_flag=True, help="Print debug logs to stderr."),
            click.option('--dry', is_flag=True, help="Doesn't perform destroy."),
            click.option('--key', '-k', help="Sources zip file bucket's name."),
            click.option('--profile_name', '-p', required=True, help="AWS credential profile."),
        ]

    @classmethod
    def multi_execute(cls, project_dir, workspace, execution_list):
        for command, options in execution_list:
            command.rm_zip(**options)
            command.terraform_destroy(**options)

    def __init__(self, app=None, name='destroy'):
        super().__init__(app, name=name)

    def rm_zip(self, *, module, bucket, key, profile_name, dry, debug, **options):
        aws_s3_session = AwsS3Session(profile_name=profile_name)

        # Removes zip file from S3
        key = key if key else f"{module}-{self.app.name}"
        if debug:
            name = f"{module}-{options['service']}"
            where = f"{bucket}/{key}"
            print(f"Removing zip sources of {name} from s3: {where} {'(not done)' if dry else ''}")

        if not dry:
            aws_s3_session.client.delete_object(Bucket=bucket, Key=key)
            aws_s3_session.client.delete_object(Bucket=bucket, Key=f"{key}.b64sha256")
            if debug:
                print(f"Successfully removed sources at s3://{bucket}/{key}")

    def terraform_destroy(self, *, workspace, debug, dry, **options):
        terraform = Terraform()

        all_workspaces = options['all']
        terraform_filename = f"{self.app.name}.{self.app.ms_type}.txt"
        if not dry:

            # Get terraform resources
            try:
                targets = self.read_terraform_resources_list_file(terraform, terraform_filename, **options)
            except OSError:
                print(f"The resouces have been already removed ({terraform_filename}).")
                return

            # Destroy resources
            for w in terraform.workspace_list():
                if all_workspaces or w in ["default", workspace]:
                    print(f"Terraform destroy ({w})", flush=True)
                    terraform.destroy(w, targets)

        if all_workspaces:

            # Removing terraform resource file
            output = Path(terraform.working_dir) / terraform_filename
            if debug:
                print(f"Removing terraform resource file: {output} {'(not done)' if dry else ''}")
            if not dry:
                output.unlink(missing_ok=True)

            # Removing terraform file
            terraform_filename = f"{self.app.name}.{self.app.ms_type}.tf"
            output = Path(terraform.working_dir) / terraform_filename
            if debug:
                print(f"Removing terraform file: {output} {'(not done)' if dry else ''}")
            if not dry:
                output.unlink(missing_ok=True)


class Terraform:

    def __init__(self):
        from python_terraform import Terraform as PythonTerraform

        self.terraform = PythonTerraform(working_dir='terraform', terraform_bin_path='terraform')
        dir = Path(self.working_dir).mkdir(exist_ok=True)
        return_code, _, err = self.terraform.init(dir_or_plan=dir)
        if return_code != 0:
            raise CwsCommandError(err)

    @property
    def working_dir(self):
        return self.terraform.working_dir

    def init(self):
        return_code, _, err = self.terraform.init()
        if return_code != 0:
            raise CwsCommandError(err)

    def apply(self, workspace, targets):
        self.select_workspace(workspace)
        return_code, _, err = self.terraform.apply(target=targets, skip_plan=True, input=False, raise_on_error=False)
        if return_code != 0:
            raise CwsCommandError(err)

    def destroy(self, workspace, targets):
        self.select_workspace(workspace)
        return_code, _, err = self.terraform.destroy(target=targets)
        if return_code != 0:
            raise CwsCommandError(err)

    def output(self):
        self.select_workspace("default")
        values = self.terraform.output(capture_output=True)
        return {key: value['value'] for key, value in values.items()} if values else "{}"

    def workspace_list(self):
        self.select_workspace("default")
        return_code, out, err = self.terraform.cmd('workspace', 'list')
        if return_code != 0:
            raise CwsCommandError(err)
        values = out[1:].translate(str.maketrans('', '', ' \t\r')).split('\n')
        return filter(None, values)

    def select_workspace(self, workspace):
        return_code, out, err = self.terraform.workspace('select', workspace)
        if workspace != 'default' and return_code != 0:
            _, out, err = self.terraform.workspace('new', workspace, raise_on_error=True)
        if not (Path(self.working_dir) / '.terraform').exists():
            self.terraform.init(input=False, raise_on_error=True)
