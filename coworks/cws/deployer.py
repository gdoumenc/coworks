import itertools
import logging
import sys
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
from ..config import CORSConfig
from ..coworks import TechMicroService

UID_SEP = '_'


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


class CwsTerraformDeployer(CwsCommand):
    """ Deploiement in 4 steps:
    create
        Step 1. Create API in default workspace (destroys API integrations made in previous deployment)
        Step 2. Create Lambda in stage workspace (destroys API deployment made in previous deployment)
    update
        Step 3. Update API routes integrations
        Step 4. Update API deployment
    """

    ZIP_CMD = 'zip'
    WRITER_CMD = 'export'

    @classmethod
    def multi_execute(cls, project_dir, workspace, client_options, execution_context):
        terraform = Terraform()
        output = client_options.pop('output', False)

        if output:
            cls._terraform_output_local(terraform)
            return

        # If one command is dry all are dry
        dry = client_options.get('dry') or client_options.get('stop') is not None
        for command, options in execution_context:
            dry = dry or options['dry']

        # Validates create option choice
        create = client_options.pop('create', False)
        if create:
            prompts = chain(["Are you sure you want to (re)create the API [yN]?:"], repeat("Answer [yN]: "))
            replies = map(input, prompts)
            valid_response = next(filter(lambda x: x == 'y' or x == 'n' or x == '', replies))
            if valid_response != 'y':
                return

        # Transfert zip file to S3 (to be done on each service)
        key = None
        for command, options in execution_context:
            print(f"Uploading zip to S3")
            key = options.pop('key') or f"{cls.bucket_key(command, options)}/archive.zip"
            ignore = options.pop('ignore') or ['terraform', '.terraform']
            command.app.execute(cls.ZIP_CMD, key=key, ignore=ignore, **options)

        # Generates terraform files (create step)
        for command, options in execution_context:
            debug = client_options.get('debug') or options['debug']
            profile_name = client_options.get('profile_name') or options['profile_name']
            aws_region = boto3.Session(profile_name=profile_name).region_name

            if not dry or options.get('stop') == 'create':
                if debug:
                    print(f"Generate terraform files for creating API and lambdas for {command.app.name}")
                output = str(Path(terraform.working_dir) / f"{command.app.name}.tf")
                command.app.execute(cls.WRITER_CMD, template=["terraform.j2"], output=output, aws_region=aws_region,
                                    step="create", key=key, entries=_entries(command.app), **options)

        # Apply terraform if not dry (create step)
        if not dry:
            msg = ["Create API", "Create lambda"] if create else ["Update API", "Update lambda"]
            cls._terraform_apply_local(terraform, workspace, msg)

        # Generates terraform files (update step)
        for command, options in execution_context:
            debug = client_options.get('debug') or options['debug']
            profile_name = client_options.get('profile_name') or options['profile_name']
            aws_region = boto3.Session(profile_name=profile_name).region_name

            if not dry or options.get('stop') == 'update':
                if debug:
                    print(f"Generate terraform files for updating API for {command.app.name}")
                output = str(Path(terraform.working_dir) / f"{command.app.name}.tf")
                command.app.execute(cls.WRITER_CMD, template=["terraform.j2"], output=output, aws_region=aws_region,
                                    step="update", key=key, entries=_entries(command.app), **options)

        # Apply terraform if not dry (update step)
        if not dry:
            cls._terraform_apply_local(terraform, workspace, ["Update API routes", f"Deploy API {workspace}"])

        cls._terraform_output_local(terraform)

    def __init__(self, app=None, name='deploy'):
        self.zip_cmd = self.add_zip_command(app)
        self.writer_cmd = self.add_writer_command(app)
        super().__init__(app, name=name)

    def add_zip_command(self, app):
        """Default zip command added if not already defined."""
        return app.commands.get(self.ZIP_CMD) or CwsZipArchiver(app)

    def add_writer_command(self, app):
        """Default writer command added if not already defined."""
        return app.commands.get(self.WRITER_CMD) or CwsTemplateWriter(app)

    @property
    def options(self):
        return [
            *super().options,
            *self.zip_cmd.options,
            click.option('--binary_media_types'),
            click.option('--create', '-c', is_flag=True, help="May create or recreate the API."),
            click.option('--layers', '-l', multiple=True),
            click.option('--memory_size', default=128),
            click.option('--output', '-o', is_flag=True, help="Print terraform output values."),
            click.option('--stop', type=click.Choice(['create', 'update']), help="Stop the terraform generation"),
            click.option('--timeout', default=30),
        ]

    @classmethod
    def bucket_key(cls, command, options):
        return command.app.name

    @staticmethod
    def _terraform_output_local(terraform):
        out = terraform.output_local("default")
        print(f"terraform output : {out}")

    @staticmethod
    def _terraform_apply_local(terraform, workspace, traces):
        stop = False

        def display_spinning_cursor():
            spinner = itertools.cycle('|/-\\')
            while not stop:
                sys.stdout.write(next(spinner))
                sys.stdout.write('\b')
                sys.stdout.flush()
                sleep(0.1)

        """
        In the default terraform workspace, we have the API.
        In the specific workspace, we have the correspondingg stagging lambda.
        """
        spin_thread = Thread(target=display_spinning_cursor)
        spin_thread.start()

        try:
            print(f"Terraform apply ({traces[0]})", flush=True)
            terraform.apply_local("default")
            print(f"Terraform apply ({traces[1]})", flush=True)
            terraform.apply_local(workspace)
        finally:
            stop = True

    def _execute(self, step=None, output=None, **options):
        raise CwsCommandError("Not implemented")


logging.getLogger("python_terraform").setLevel(logging.ERROR)


class Terraform:

    def __init__(self):
        from python_terraform import Terraform as PythonTerraform

        self.terraform = PythonTerraform(working_dir='terraform', terraform_bin_path='terraform')
        Path(self.working_dir).mkdir(exist_ok=True)

    @property
    def working_dir(self):
        return self.terraform.working_dir

    def apply_local(self, workspace):
        self._select_workspace(workspace)
        return_code, _, err = self.terraform.apply(skip_plan=True, input=False, raise_on_error=False, parallelism=1)
        if return_code != 0:
            raise CwsCommandError(err)

    def output_local(self, workspace):
        self._select_workspace(workspace)
        values = self.terraform.output(capture_output=True)
        return {key: value['value'] for key, value in values.items()} if values else "{}"

    def _select_workspace(self, workspace):
        return_code, out, err = self.terraform.workspace('select', workspace)
        if workspace != 'default' and return_code != 0:
            _, out, err = self.terraform.workspace('new', workspace, raise_on_error=True)
        if not (Path(self.working_dir) / '.terraform').exists():
            self.terraform.init(input=False, raise_on_error=True)


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
