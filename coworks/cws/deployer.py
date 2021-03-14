import itertools
import logging
import sys
from abc import ABC
from dataclasses import dataclass
from itertools import chain, repeat
from pathlib import Path
from threading import Thread
from time import sleep
from typing import List

import boto3
import click

from .command import CwsCommand, CwsCommandError
from .writer import CwsTemplateWriter
from .zip import CwsZipArchiver
from .. import aws
from ..config import CORSConfig
from ..coworks import TechMicroService

UID_SEP = '_'


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
    def generate_terraform_files(cls, step, app, terraform, msg, key, **options):
        debug = options['debug']
        dry = options['dry']
        profile_name = options['profile_name']
        aws_region = boto3.Session(profile_name=profile_name).region_name

        if not dry or options.get('stop') == step:
            if debug:
                print(msg)
            output = str(Path(terraform.working_dir) / f"{app.name}.tf")
            app.execute(cls.WRITER_CMD, template=["terraform.j2"], output=output, aws_region=aws_region,
                        step=step, key=key, entries=_entries(app), **options)


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
            click.option('--create', '-c', is_flag=True, help="May create or recreate the API."),
            click.option('--dry', is_flag=True, help="Doesn't perform deploy."),
            click.option('--layers', '-l', multiple=True),
            click.option('--output', '-o', is_flag=True, help="Print terraform output values."),
            click.option('--stop', type=click.Choice(['create', 'update']), help="Stop the terraform generation"),
        ]

    @classmethod
    def multi_execute(cls, project_dir, workspace, execution_list):
        terraform = Terraform()
        terraform.init()

        # output, dry and create are global options
        dry = create = False
        for command, options in execution_list:
            dry = dry or options.pop('dry', False)
            create = create or options.pop('create', False)

            # set default key value
            options['key'] = options['key'] or f"{command.app.name}/archive.zip"

            # Only print output
            output = options.pop('output', False)
            if output:
                print(f"terraform output : {terraform.output()}")
                return

        # Validates create option choice
        if create:
            prompts = chain(["Are you sure you want to (re)create the API [yN]?:"], repeat("Answer [yN]: "))
            replies = map(input, prompts)
            valid_response = next(filter(lambda x: x == 'y' or x == 'n' or x == '', replies))
            if valid_response != 'y':
                return

        # Transfert zip file to S3 (to be done on each service)
        for command, options in execution_list:
            print(f"Uploading zip to S3")
            module_name = options.pop('module_name')
            ignore = options.pop('ignore') or ['terraform', '.terraform']
            command.app.execute(cls.ZIP_CMD, ignore=ignore, module_name=module_name, **options)

        # Generates default provider
        cls.generate_common_terraform_files()

        # Generates terraform files (create step)
        for command, options in execution_list:
            msg = f"Generate terraform files for creating API and lambdas for {command.app.name}"
            cls.generate_terraform_files("create", command.app, terraform, msg, dry=dry, **options)

        # Apply terraform if not dry (create API with null resources and lambda step)
        if not dry:
            msg = ["Create API", "Create lambda"] if create else ["Update API", "Update lambda"]
            cls.terraform_apply(terraform, workspace, msg)

        # Generates terraform files (update step)
        for command, options in execution_list:
            msg = f"Generate terraform files for updating API routes and deploiement for {command.app.name}"
            cls.generate_terraform_files("update", command.app, terraform, msg, dry=dry, **options)

        # Apply terraform if not dry (update API routes and deploy step)
        if not dry:
            msg = ["Update API routes", f"Deploy API {workspace}"]
            cls.terraform_apply(terraform, workspace, msg)

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
    def terraform_apply(terraform, workspace, traces):
        stop = False

        def display_spinning_cursor():
            spinner = itertools.cycle('|/-\\')
            while not stop:
                sys.stdout.write(next(spinner))
                sys.stdout.write('\b')
                sys.stdout.flush()
                sleep(0.1)

        # In the default terraform workspace, we have the API.
        # In the specific workspace, we have the correspondingg stagging lambda.
        spin_thread = Thread(target=display_spinning_cursor)
        spin_thread.start()

        try:
            print(f"Terraform apply ({traces[0]})", flush=True)
            terraform.apply("default")
            print(f"Terraform apply ({traces[1]})", flush=True)
            terraform.apply(workspace)
        finally:
            stop = True


class CwsTerraformDestroyer(CwsTerraformCommand):

    @property
    def options(self):
        return [
            *super().options,
            click.option('--bucket', '-b', help="Bucket to remove sources zip file from", required=True),
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
        aws_s3_session = aws.AwsS3Session(profile_name=profile_name)

        # Removes zip file from S3
        key = key if key else f"{module}-{self.app.name}"
        if debug:
            name = f"{module}-{options['service']}"
            where = f"{bucket}/{key}"
            print(f"Removing zip sources of {name} from s3:{where} {'(not done)' if dry else ''}")

        aws_s3_session.client.delete_object(Bucket=bucket, Key=key)
        aws_s3_session.client.delete_object(Bucket=bucket, Key=f"{key}.b64sha256")
        if debug:
            print(f"Successfully removed sources at s3://{bucket}/{key}")

    def terraform_destroy(self, *, workspace, **options):
        terraform = Terraform()

        msg = f"Generate terraform files for creating API and lambdas for {self.app.name}"
        self.generate_terraform_files("create", self.app, terraform, msg, **options)

        for w in terraform.workspace_list():
            if w in ["default", workspace]:
                print(f"Terraform destroy ({w})", flush=True)
                terraform.destroy(w)


logging.getLogger("python_terraform").setLevel(logging.ERROR)


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

    def apply(self, workspace):
        self.select_workspace(workspace)
        return_code, _, err = self.terraform.apply(skip_plan=True, input=False, raise_on_error=False, parallelism=1)
        if return_code != 0:
            raise CwsCommandError(err)

    def destroy(self, workspace):
        self.select_workspace(workspace)
        return_code, _, err = self.terraform.destroy()
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


@dataclass
class TerraformEntry:
    app: TechMicroService
    parent_uid: str
    path: str
    methods: List[str]
    cors: CORSConfig

    @property
    def uid(self):
        def remove_brackets(path):
            return f"{path.replace('{', '').replace('}', '')}"

        if self.path is None:
            return UID_SEP

        last = remove_brackets(self.path)
        return f"{self.parent_uid}{UID_SEP}{last}" if self.parent_uid else last

    @property
    def is_root(self):
        return self.path is None

    @property
    def parent_is_root(self):
        return self.parent_uid == UID_SEP

    def __repr__(self):
        return f"{self.uid}:{self.methods}"


def _entries(app):
    """Returns the list of flatten path (prev, last, keys)."""
    all_pathes_id = {}

    def add_entry(previous, last, meth):
        entry = TerraformEntry(app, previous, last, meth, app.config.cors)
        uid = entry.uid
        if uid not in all_pathes_id:
            all_pathes_id[uid] = entry
        if all_pathes_id[uid].methods is None:
            all_pathes_id[uid].methods = meth
        return uid

    for route, methods in app.routes.items():
        previous_uid = UID_SEP
        splited_route = route[1:].split('/')

        # special root case
        if splited_route == ['']:
            add_entry(None, None, methods.keys())
            continue

        # creates intermediate resources
        last_path = splited_route[-1:][0]
        for prev in splited_route[:-1]:
            previous_uid = add_entry(previous_uid, prev, None)

        # set entry keys for last entry
        add_entry(previous_uid, last_path, methods.keys())

    return all_pathes_id
