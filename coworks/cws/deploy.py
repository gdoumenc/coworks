from dataclasses import dataclass

import boto3
import click
import inspect
import itertools
import subprocess
import sys
import typing as t
from flask.cli import pass_script_info
from flask.cli import with_appcontext
from jinja2 import Environment
from jinja2 import PackageLoader
from jinja2 import select_autoescape
from pathlib import Path
from shutil import copy
from subprocess import CalledProcessError, CompletedProcess
from threading import Thread
from time import sleep
from werkzeug.routing import Rule

from .zip import zip_command
from .. import TechMicroService

UID_SEP = '_'


@dataclass
class TerraformResource:
    parent_uid: str
    path: str
    rules: t.List[Rule] = None

    @property
    def uid(self) -> str:
        def remove_variable(path):
            return f"{path.replace('<', '').replace('>', '')}"

        if self.path is None:
            return ''

        last = remove_variable(self.path)
        return f"{self.parent_uid}{UID_SEP}{last}" if self.parent_uid else last

    @property
    def is_root(self) -> bool:
        return self.path is None

    @property
    def parent_is_root(self) -> bool:
        return self.parent_uid == ''

    def __repr__(self):
        return f"{self.uid}:{self.rules}"


class Terraform:

    def __init__(self, working_dir: Path = 'terraform', timeout: int = 240):
        self.working_dir = working_dir
        Path(self.working_dir).mkdir(exist_ok=True)
        self.timeout = timeout

    def init(self):
        self.__execute(['init', '-input=false'])

    def apply(self, workspace) -> None:
        self.select_workspace(workspace)
        self.__execute(['apply', '-auto-approve', '-parallelism=1'])

    def destroy(self, workspace) -> None:
        self.select_workspace(workspace)
        self.__execute(['apply', '-destroy', '-auto-approve', '-parallelism=1'])
        if workspace != "default":
            self.__execute(['workspace', 'delete', workspace])

    def output(self):
        self.select_workspace("default")
        values = self.__execute(['output']).stdout
        return values.decode("utf-8").strip()

    def workspace_list(self):
        self.select_workspace("default")
        values = self.__execute(['workspace', 'list']).stdout
        values = values[1:].decode("utf-8").split('\n')
        return [w.strip() for w in filter(None, values)]

    def select_workspace(self, workspace) -> None:
        if not (Path(self.working_dir) / '.terraform').exists():
            self.init()
        try:
            self.__execute(["workspace", "select", workspace])
        except CalledProcessError:
            self.__execute(["workspace", "new", workspace])

    def api_resources(self, app: TechMicroService):
        """Returns the list of flatten path (prev_uid, last, rule)."""
        resources = {}

        def add_rule(previous: t.Optional[str], last: t.Optional[str], rule_: t.Optional[Rule]):

            # Creates the terraform ressource if doesn't exist.
            resource = TerraformResource(previous, last)
            uid = resource.uid
            if uid not in resources:
                resources[uid] = resource

            resource = resources[uid]
            if resources[uid].rules is None:
                resources[uid].rules = [rule_]
            else:
                resources[uid].rules.append(rule_)
            return uid

        for rule in app.url_map.iter_rules():
            route = rule.rule
            previous_uid = ''
            if route.startswith('/'):
                route = route[1:]
            splited_route = route.split('/')

            # special root case
            if splited_route == ['']:
                add_rule(None, None, rule)
                continue

            # creates intermediate resources
            last_path = splited_route[-1:][0]
            for prev in splited_route[:-1]:
                previous_uid = add_rule(previous_uid, prev, None)

            # set entry keys for last entry
            add_rule(previous_uid, last_path, rule)

        return resources

    @property
    def jinja_env(self) -> Environment:
        return Environment(loader=PackageLoader(sys.modules[__name__].__package__),
                           autoescape=select_autoescape(['html', 'xml']))

    def generate_common_files(self, workspace) -> None:
        pass

    def generate_files(self, info, config, template_filename, output_filename, **options) -> None:
        app = info.load_app()
        project_dir = options['project_dir']
        workspace = options['workspace']
        debug = options['debug']
        profile_name = options['profile_name']
        aws_region = boto3.Session(profile_name=profile_name).region_name

        if debug:
            click.echo(f"Generate terraform files for updating API routes and deploiement for {app.name}")

        data = {
            'account_number': options.get('account_number'),
            'api_resources': self.api_resources(app),
            'app': app,
            'app_import_path': info.app_import_path.replace(':', '.') if info.app_import_path else "app.app",
            'aws_region': aws_region,
            'description': inspect.getdoc(app) or "",
            'environment_variables': config.environment_variables,
            'environment_variable_files': config.existing_environment_variables_files(project_dir),
            # 'module': app.__module__,
            # 'module_dir': pathlib.PurePath(*module_path[:-1]),
            # 'module_file': app.__module__,
            # 'module_path': pathlib.PurePath(*module_path),
            'ms_name': app.name,
            'project_dir': project_dir,
            # 'source_file': pathlib.PurePath(project_dir, *module_path),
            'workspace': workspace,
            **options
        }
        template = self.jinja_env.get_template(template_filename)
        output = Path(self.working_dir) / output_filename
        with output.open("w") as f:
            f.write(template.render(**data))

    def create_stage(self, workspace: str) -> None:
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
            click.echo(f"Terraform apply (Create API routes)")
            self.apply("default")
            click.echo(f"Terraform apply (Deploy API and Lambda for the {workspace} stage)")
            self.apply(workspace)
        finally:
            stop = True

    def __execute(self, cmd_args: t.List[str]) -> CompletedProcess:
        p = subprocess.run(["terraform", *cmd_args], capture_output=True, cwd=self.working_dir, timeout=self.timeout)
        p.check_returncode()
        return p


@click.command("deploy", short_help="Deploy the Flask server on AWS Lambda.")
# Zip options (redefined)
@click.option('--bucket', '-b', help="Bucket to upload sources zip file to", required=True)
@click.option('--dry', is_flag=True, help="Doesn't perform deploy [Global option only].")
@click.option('--ignore', '-i', multiple=True, help="Ignore pattern.")
@click.option('--key', '-k', help="Sources zip file bucket's name.")
@click.option('--module_name', '-m', multiple=True, help="Python module added from current pyenv (module or file.py).")
@click.option('--profile_name', '-p', required=True, help="AWS credential profile.")
# Deploy specific options
@click.option('--binary-media-types')
@click.option('--cloud', is_flag=True, help="Use cloud workspaces.")
@click.option('--layers', '-l', multiple=True, help="Add layer (full arn: aws:lambda:...)")
@click.option('--memory-size', default=128)
@click.option('--output', '-o', is_flag=True, help="Print terraform output values.")
@click.option('--python', '-p', type=click.Choice(['3.7', '3.8']), default='3.8',
              help="Python version for the lambda.")
@click.option('--timeout', default=60)
@click.option('--terraform-class', default=Terraform, hidden=True)
@click.pass_context
@pass_script_info
@with_appcontext
def deploy_command(info, ctx, output, terraform_class, **options) -> None:
    """ Deploiement in 2 steps:
        Step 1. Create API and routes integrations
        Step 2. Deploy API and Lambda
    """
    print(terraform_class)
    exit()
    terraform = terraform_class()

    if output:  # Stop if only print output
        click.echo(f"terraform output : {terraform.output()}")
        return

    # Set default options calculated value
    app = info.load_app()
    options['hash'] = True
    options['ignore'] = options['ignore'] or ['.*', 'terraform']
    options['key'] = options['key'] or f"{app.__module__}-{app.name}/archive.zip"

    # Transfert zip file to S3 (to be done on each service)
    zip_options = {zip_param.name: options[zip_param.name] for zip_param in zip_command.params}
    ctx.invoke(zip_command, **zip_options)

    root_command_params = ctx.find_root().params
    project_dir = root_command_params['project_dir']
    workspace = root_command_params['workspace']
    dry = zip_options.get('dry')

    # Copy environment files
    config = app.get_config(workspace)
    environment_variable_files = [p.as_posix() for p in
                                  config.existing_environment_variables_files(project_dir)]
    for file in environment_variable_files:
        copy(file, terraform.working_dir)

    # Generates common terraform files
    terraform.generate_common_files(workspace)

    # Generates terraform files and copy environment variable files in terraform working dir for provisionning
    terraform_filename = f"{app.name}.{app.ms_type}.tf"
    terraform.generate_files(info, config, "deploy.j2", terraform_filename, **root_command_params, **options)

    # Apply terraform if not dry
    if not dry:
        terraform.create_stage(workspace)

    # Traces output
    click.echo(f"terraform output :\n{terraform.output()}")

# class CwsTerraformCommand(CwsCommand, ABC):
#     WRITER_CMD = 'export'
#
#     terraform = Terraform()
#
#     @property
#     def options(self):
#         return [
#             *super().options,
#             click.option('--terraform-timeout', default=60),
#         ]
#
#     def __init__(self, app=None, **kwargs):
#         super().__init__(app, **kwargs)
#         self.writer_cmd = self.add_writer_command(app)
#
#     def add_writer_command(self, app):
#         """Default writer command added if not already defined.
#         Defined as function to be redefined in subclass if needed."""
#         return app.commands.get(self.WRITER_CMD) or CwsTemplateWriter(app)
#
#     def generate_terraform_files(self, template, filename, msg, **options):
#         debug = options['debug']
#         profile_name = options['profile_name']
#         aws_region = boto3.Session(profile_name=profile_name).region_name
#
#         if debug:
#             print(msg)
#
#         output = str(Path(self.terraform.working_dir) / filename)
#         self.app.execute(self.WRITER_CMD, template=[template], output=output, aws_region=aws_region,
#                          api_resources=self.terraform_api_resources(), **options)
#
#     def terraform_api_resources(self):
#         """Returns the list of flatten path (prev, last, entry)."""
#         resources = {}
#
#         def add_entries(previous, last, entries_: Optional[Dict[str, Entry]]):
#             ter_entry = TerraformResource(previous, last, entries_, self.app.config.cors)
#             uid = ter_entry.uid
#             if uid not in resources:
#                 resources[uid] = ter_entry
#             if resources[uid].entries is None:
#                 resources[uid].entries = entries_
#             return uid
#
#         for route, entries in self.app.entries.items():
#             previous_uid = ''
#             if route.startswith('/'):
#                 route = route[1:]
#             splited_route = route.split('/')
#
#             # special root case
#             if splited_route == ['']:
#                 add_entries(None, None, entries)
#                 continue
#
#             # creates intermediate resources
#             last_path = splited_route[-1:][0]
#             for prev in splited_route[:-1]:
#                 previous_uid = add_entries(previous_uid, prev, None)
#
#             # set entry keys for last entry
#             add_entries(previous_uid, last_path, entries)
#
#         return resources
#
#
# class CwsTerraformDeployer(CwsTerraformCommand):
#     """ Deploiement in 2 steps:
#         Step 1. Create API and routes integrations
#         Step 2. Deploy API and Lambda
#     """
#
#     ZIP_CMD = 'zip'
#
#     @property
#     def options(self):
#         return [
#             *super().options,
#             *self.zip_cmd.options,
#             click.option('--binary-media-types'),
#             click.option('--cloud', is_flag=True, help="Use cloud workspaces."),
#             click.option('--dry', is_flag=True, help="Doesn't perform deploy [Global option only]."),
#             click.option('--layers', '-l', multiple=True, help="Add layer (full arn: aws:lambda:...)"),
#             click.option('--memory-size', default=128),
#             click.option('--output', '-o', is_flag=True, help="Print terraform output values."),
#             click.option('--python', '-p', type=click.Choice(['3.7', '3.8']), default='3.8',
#                          help="Python version for the lambda."),
#             click.option('--timeout', default=60),
#         ]
#
#     @classmethod
#     def multi_execute(cls, project_dir, workspace, execution_list):
#         # Output, dry are global options
#         dry = output = False
#         for command, options in execution_list:
#             dry = options.pop('dry', False) or dry
#
#             # Set default bucket key value
#             options['key'] = options['key'] or f"{options.get('module')}-{command.app.name}/archive.zip"
#             output = output or options.pop('output', False)
#
#         if output:  # Stop if only print output
#             print(f"terraform output : {cls.terraform.output()}", flush=True)
#             return
#
#         # Transfert zip file to S3 (to be done on each service)
#         for command, options in execution_list:
#             print(f"Uploading zip to S3")
#             module_name = options.pop('module_name')
#             ignore = options.pop('ignore') or ['.*', 'terraform']
#             options.pop('hash')
#             command.app.execute(cls.ZIP_CMD, ignore=ignore, module_name=module_name, hash=True, dry=dry, **options)
#
#         # Generates common terraform files
#         cls.generate_common_terraform_files(workspace, execution_list)
#
#         # Generates terraform files and copy environment variable files in terraform working dir for provisionning
#         for command, options in execution_list:
#             terraform_filename = f"{command.app.name}.{command.app.ms_type}.tf"
#             msg = f"Generate terraform files for updating API routes and deploiement for {command.app.name}"
#             command.generate_terraform_files("deploy.j2", terraform_filename, msg, dry=dry, **options)
#
#             config = command.app.get_config(workspace)
#             environment_variable_files = [p.as_posix() for p in
#                                           config.existing_environment_variables_files(project_dir)]
#             for file in environment_variable_files:
#                 copy(file, cls.terraform.working_dir)
#
#         # Apply terraform if not dry
#         if not dry:
#             msg = ["Create API routes", f"Deploy API and Lambda for the {workspace} stage"]
#             cls.terraform_apply(workspace, msg)
#
#         # Traces output
#         print(f"terraform output : {cls.terraform.output()}", flush=True)
#
#     @classmethod
#     def generate_common_terraform_files(cls, workspace, execution_list):
#         pass
#
#     def __init__(self, app=None, name='deploy'):
#         self.zip_cmd = self.add_zip_command(app)
#         super().__init__(app, name=name)
#
#     def add_zip_command(self, app):
#         """Default zip command added if not already defined."""
#         return app.commands.get(self.ZIP_CMD) or CwsZipArchiver(app)
#
#     @classmethod
#     def terraform_apply(cls, workspace, traces):
#         """In the default terraform workspace, we have the API.
#         In the specific workspace, we have the corresponding stagging lambda.
#         """
#         stop = False
#
#         def display_spinning_cursor():
#             spinner = itertools.cycle('|/-\\')
#             while not stop:
#                 sys.stdout.write(next(spinner))
#                 sys.stdout.write('\b')
#                 sys.stdout.flush()
#                 sleep(0.1)
#
#         spin_thread = Thread(target=display_spinning_cursor)
#         spin_thread.start()
#
#         try:
#             print(f"Terraform apply ({traces[0]})", flush=True)
#             cls.terraform.apply("default")
#             print(f"Terraform apply ({traces[1]})", flush=True)
#             cls.terraform.apply(workspace)
#         finally:
#             stop = True
#
#
# class CwsTerraformDestroyer(CwsTerraformCommand):
#
#     @property
#     def options(self):
#         return [
#             *super().options,
#             click.option('--all', '-a', is_flag=True, help="Destroy on all workspaces."),
#             click.option('--bucket', '-b', help="Bucket to remove sources zip file from.", required=True),
#             click.option('--debug', is_flag=True, help="Print debug logs to stderr."),
#             click.option('--dry', is_flag=True, help="Doesn't perform destroy."),
#             click.option('--key', '-k', help="Sources zip file bucket's name."),
#             click.option('--profile_name', '-p', required=True, help="AWS credential profile."),
#         ]
#
#     @classmethod
#     def multi_execute(cls, project_dir, workspace, execution_list):
#         for command, options in execution_list:
#             command.rm_zip(**options)
#             command.terraform_destroy(**options)
#
#     def __init__(self, app=None, name='destroy'):
#         super().__init__(app, name=name)
#
#     def rm_zip(self, *, module, bucket, key, profile_name, dry, debug, **options):
#         aws_s3_session = AwsS3Session(profile_name=profile_name)
#
#         # Removes zip file from S3
#         key = key if key else f"{module}-{self.app.name}"
#         if debug:
#             name = f"{module}-{options['service']}"
#             where = f"{bucket}/{key}"
#             print(f"Removing zip sources of {name} from s3: {where} {'(not done)' if dry else ''}")
#
#         if not dry:
#             aws_s3_session.client.delete_object(Bucket=bucket, Key=key)
#             aws_s3_session.client.delete_object(Bucket=bucket, Key=f"{key}.b64sha256")
#             if debug:
#                 print(f"Successfully removed sources at s3://{bucket}/{key}")
#
#     def terraform_destroy(self, *, project_dir, workspace, debug, dry, **options):
#         all_workspaces = options['all']
#         terraform_resources_filename = f"{self.app.name}.{self.app.ms_type}.txt"
#         if not dry:
#             # perform dry deployment to have updated terraform files
#             cmds = ['cws', '-p', project_dir, '-w', workspace, 'deploy', '--dry']
#             p = subprocess.run(cmds, capture_output=True, timeout=self.terraform.timeout)
#
#             # Destroy resources (except default)
#             for w in self.terraform.workspace_list():
#                 if w in [workspace] or (all_workspaces and w != 'default'):
#                     print(f"Terraform destroy ({w})", flush=True)
#                     self.terraform.destroy(w)
#
#             if all_workspaces:
#
#                 # Removes default workspace
#                 self.terraform.destroy('default')
#
#                 # Removes terraform file
#                 terraform_filename = f"{self.app.name}.{self.app.ms_type}.tf"
#                 output = Path(self.terraform.working_dir) / terraform_filename
#                 if debug:
#                     print(f"Removing terraform file: {output} {'(not done)' if dry else ''}")
#                 if not dry:
#                     output.unlink(missing_ok=True)
#                     terraform_filename = f"{self.app.name}.{self.app.ms_type}.tf"
#                     msg = f"Generate minimal destroy file for {self.app.name}"
#                     self.generate_terraform_files("destroy.j2", terraform_filename, msg, dry=dry, debug=debug,
#                                                   **options)
#
#         self.terraform.select_workspace("default")
