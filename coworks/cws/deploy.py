import inspect
import subprocess
import sys
import typing as t
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from shutil import copy
from subprocess import CalledProcessError
from subprocess import CompletedProcess

import boto3
import click
from flask.cli import pass_script_info
from flask.cli import with_appcontext
from jinja2 import BaseLoader
from jinja2 import Environment
from jinja2 import PackageLoader
from jinja2 import select_autoescape
from werkzeug.routing import Rule

from .exception import ExitCommand
from .utils import progressbar
from .zip import zip_command

UID_SEP = '_'


@dataclass
class TerraformResource:
    parent_uid: str
    path: str
    rules: t.List[Rule] = None

    @cached_property
    def uid(self) -> str:

        if self.is_root:
            return ''

        uid = self.path.replace('{', '').replace('}', '')

        if self.parent_is_root:
            return uid

        return f"{self.parent_uid}{UID_SEP}{uid}" if self.path else self.parent_uid

    @cached_property
    def is_root(self) -> bool:
        return self.path is None

    @cached_property
    def parent_is_root(self) -> bool:
        return self.parent_uid == ''

    # noinspection PyUnresolvedReferences
    @cached_property
    def no_cors_methods(self) -> t.List[t.Optional[str]]:
        return [rule.methods for rule in self.rules if rule.cws_no_cors]

    def __repr__(self):
        return f"{self.uid}:{self.rules}"


class TerraformLocal:
    """Terraform class to manage local terraform deployements."""
    TIMEOUT = 600

    def __init__(self, info, bar, **options):
        self.info = info
        self.bar = bar
        self.working_dir = Path(options['terraform_dir'])
        self.working_dir.mkdir(exist_ok=True)

    def init(self):
        self._execute(['init', '-input=false'])

    def apply(self, workspace) -> None:
        self.select_workspace(workspace)
        self._execute(['apply', '-auto-approve', '-parallelism=1'])

    def destroy(self, workspace) -> None:
        self.select_workspace(workspace)
        self._execute(['apply', '-destroy', '-auto-approve', '-parallelism=1'])
        if workspace != "default":
            self._execute(['workspace', 'delete', workspace])

    def output(self):
        self.select_workspace("default")
        values = self._execute(['output']).stdout
        return values.decode("utf-8").strip()

    def workspace_list(self):
        self.select_workspace("default")
        values = self._execute(['workspace', 'list']).stdout
        values = values[1:].decode("utf-8").split('\n')
        return [w.strip() for w in filter(None, values)]

    def select_workspace(self, workspace) -> None:
        if not (self.working_dir / '.terraform').exists():
            self.init()
        try:
            self._execute(["workspace", "select", workspace])
        except CalledProcessError:
            self._execute(["workspace", "new", workspace])

    @cached_property
    def app(self):
        return self.info.load_app()

    @property
    def api_resources(self):
        """Returns the list of flatten path (prev_uid, last, rule)."""
        resources: t.Dict[str, TerraformResource] = {}

        def add_rule(previous: t.Optional[str], path: t.Optional[str], rule_: t.Optional[Rule]):
            """Add a method rule in a resource."""
            path = None if path is None else path.replace('<', '{').replace('>', '}')
            resource = TerraformResource(previous, path)
            if rule_:
                view_function = self.app.view_functions.get(rule_.endpoint)
                rule_.cws_binary = getattr(view_function, '__CWS_BINARY')
                rule_.cws_content_type = getattr(view_function, '__CWS_CONTENT_TYPE')
                rule_.cws_no_auth = getattr(view_function, '__CWS_NO_AUTH')
                rule_.cws_no_cors = getattr(view_function, '__CWS_NO_CORS')

            # Creates the terraform ressource if doesn't exist.
            uid = resource.uid
            if uid not in resources:
                resources[uid] = resource

            resource = resources[uid]
            if rule_:
                if resources[uid].rules is None:
                    resources[uid].rules = [rule_]
                else:
                    resources[uid].rules.append(rule_)
            return uid

        for rule in self.app.url_map.iter_rules():
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
            for prev in splited_route[:-1]:
                previous_uid = add_rule(previous_uid, prev, None)

            # set entry keys for last entry
            add_rule(previous_uid, splited_route[-1:][0], rule)

        return resources

    @property
    def template_loader(self) -> BaseLoader:
        return PackageLoader(sys.modules[__name__].__package__)

    @property
    def jinja_env(self) -> Environment:
        return Environment(loader=self.template_loader, autoescape=select_autoescape(['html', 'xml']))

    def get_context_data(self, **options) -> dict:
        project_dir = options['project_dir']
        workspace = options['workspace']
        config = self.app.get_config(workspace)
        environment_variable_files = config.existing_environment_variables_files(self.app)

        data = {
            'api_resources': self.api_resources,
            'app': self.app,
            'app_import_path': self.info.app_import_path,
            'aws_region': boto3.Session(profile_name=options['profile_name']).region_name,
            'description': inspect.getdoc(self.app) or "",
            'environment_variables': config.environment_variables,
            'environment_variable_files': [Path(f).name for f in environment_variable_files],
            'ms_name': self.app.name,
            **options
        }
        return data

    def generate_common_files(self, **options) -> None:
        pass

    def generate_files(self, template_filename, output_filename, **options) -> None:
        project_dir = options['project_dir']
        workspace = options['workspace']
        debug = options['debug']
        profile_name = options['profile_name']

        config = self.app.get_config(workspace)
        aws_region = boto3.Session(profile_name=profile_name).region_name

        if debug:
            self.bar.update(msg=f"Generate terraform files for updating API routes and deploiement for {self.app.name}")

        data = self.get_context_data(**options)
        template = self.jinja_env.get_template(template_filename)
        output = self.working_dir / output_filename
        with output.open("w") as f:
            f.write(template.render(**data))

    def create_stage(self, **options) -> None:
        """In the default terraform workspace, we have the API.
        In the specific workspace, we have the corresponding stagging lambda.
        """
        workspace = options['workspace']
        self.bar.update(msg=f"Terraform apply (Create API routes)")
        self.apply("default")
        if options['api']:
            return
        self.bar.update(msg=f"Terraform apply (Deploy API and Lambda for the {workspace} stage)")
        self.apply(workspace)

    def copy_file(self, file):
        copy(file, self.working_dir)
        self.bar.update()

    def _execute(self, cmd_args: t.List[str]) -> CompletedProcess:
        # with self.bar:
        p = subprocess.run(["terraform", *cmd_args], capture_output=True, cwd=self.working_dir,
                           timeout=self.TIMEOUT)
        p.check_returncode()
        return p


class RemoteTerraform(TerraformLocal):

    def select_workspace(self, workspace) -> None:
        """Workspace are defined remotly."""
        pass

    def apply(self, workspace=None) -> None:
        if not (self.working_dir / '.terraform').exists():
            try:
                self.init()
            except CalledProcessError:
                raise ExitCommand("Cannot init terraform: perhaps variables are not defined on terraform cloud.")
        self._execute(['apply', '-auto-approve', '-refresh=false'])


class TerraformCloud:
    """Terraform class to manage remote deployements. Two terraform interfaces are used:
    - One for the API,
    - One for for the stage.
    """

    def __init__(self, info, bar, **options):
        self.info = info
        self.bar = bar
        self.working_dir = Path(options['terraform_dir'])
        self.workspace = options['workspace']
        self._api_terraform = self._workspace_terraform = None

    @property
    def api_terraform(self):
        if self._api_terraform is None:
            self._api_terraform = RemoteTerraform(self.info, self.bar, terraform_dir=self.working_dir)
        return self._api_terraform

    @property
    def workspace_terraform(self):
        if self._workspace_terraform is None:
            terraform_dir = f"{self.working_dir}_{self.workspace}"
            self._workspace_terraform = RemoteTerraform(self.info, self.bar, terraform_dir=terraform_dir)
        return self._workspace_terraform

    def init(self):
        self.api_terraform.init()
        self.workspace_terraform.init()

    def apply(self, workspace) -> None:
        if workspace == "default":
            self.api_terraform.apply(workspace)
        else:
            self.workspace_terraform.apply(workspace)

    def output(self):
        api_out = self.api_terraform.output()
        return api_out

    def select_workspace(self, workspace) -> None:
        self.api_terraform.select_workspace(workspace)
        self.workspace_terraform.select_workspace(workspace)

    def generate_common_files(self, **options) -> None:
        stage = ""
        self._generate_common_file(self.api_terraform, stage=stage, **options)
        stage = f"_{options['workspace']}"
        self._generate_common_file(self.workspace_terraform, stage=stage, **options)

    def generate_files(self, template_filename, output_filename, **options) -> None:
        options_for_api = {**options, **{'stage': ''}}

        self.api_terraform.generate_files(template_filename, output_filename, **options_for_api)
        options_for_stage = {**options, **{'stage': f"_{options['workspace']}", 'debug': False}}
        self.workspace_terraform.generate_files(template_filename, output_filename, **options_for_stage)

    def create_stage(self, **options) -> None:
        """In the default terraform workspace, we have the API.
        In the specific workspace, we have the corresponding stagging lambda.
        """
        workspace = options['workspace']
        self.bar.update(msg=f"Terraform apply (Create API routes)")
        self.api_terraform.apply()
        self.bar.update(msg=f"Terraform apply (Deploy API and Lambda for the {workspace} stage)")
        self.workspace_terraform.apply()

    def copy_file(self, file):
        self.workspace_terraform.copy_file(file)

    def _generate_common_file(self, terraform, **options):
        template = terraform.jinja_env.get_template("terraform.j2")
        with open(f"{terraform.working_dir}/terraform.tf", 'w+') as f:
            data = self.api_terraform.get_context_data(**options)
            f.write(template.render(**data))


@click.command("deploy", short_help="Deploy the CoWorks microservice on AWS Lambda.")
# Zip options (redefined)
@click.option('--api', is_flag=True, help="Stop after API create step (forces also dry mode).")
@click.option('--bucket', '-b', help="Bucket to upload sources zip file to", required=True)
@click.option('--dry', is_flag=True, help="Doesn't perform deploy [Global option only].")
@click.option('--ignore', '-i', multiple=True, help="Ignore pattern.")
@click.option('--key', '-k', help="Sources zip file bucket's name.")
@click.option('--module-name', '-m', multiple=True, help="Python module added from current pyenv (module or file.py).")
@click.option('--profile-name', '-pn', required=True, help="AWS credential profile.")
# Deploy specific optionsElle est immédiatement opérationnelle et fonctionnell
@click.option('--binary-media-types')
@click.option('--cloud', is_flag=True, help="Use cloud workspaces.")
@click.option('--layers', '-l', multiple=True, help="Add layer (full arn: aws:lambda:...)")
@click.option('--memory-size', default=128)
@click.option('--output', '-o', is_flag=True, help="Print terraform output values.")
@click.option('--python', '-p', type=click.Choice(['3.7', '3.8']), default='3.8',
              help="Python version for the lambda.")
@click.option('--source', help="Header identification token source.")
@click.option('--timeout', default=60)
@click.option('--terraform-dir', default="terraform")
@click.pass_context
@pass_script_info
@with_appcontext
def deploy_command(info, ctx, output, terraform_class=TerraformLocal, **options) -> None:
    """ Deploiement in 2 steps:
        Step 1. Create API and routes integrations
        Step 2. Deploy API and Lambda
    """
    root_command_params = ctx.find_root().params
    project_dir = root_command_params['project_dir']
    workspace = root_command_params['workspace']
    debug = root_command_params['debug']

    with progressbar(label='Deploy microservice', threaded=True) as bar:
        try:
            if info.app_import_path and '/' in info.app_import_path:
                msg = f"Cannot deploy a project with handler not on project folder : {info.app_import_path}.\n"
                msg += f"Add option -p {'/'. join(info.app_import_path.split('/')[:-1])} to resolve this."""
                bar.terminate(msg)
                return

            info.app_import_path = info.app_import_path.replace(':', '.') if info.app_import_path else "app.app"
            if '.' not in info.app_import_path:
                msg = f"FLASK_APP must be in form 'module:variable' but is {info.app_import_path}."
                bar.terminate(msg)
                return

            terraform = terraform_class(info, bar, **root_command_params, **options)
            if output:  # Stop if only print output
                bar.terminate(f"terraform output : {terraform.output()}")
                return

            # Set default options calculated value
            app = info.load_app()
            options['hash'] = True
            options['ignore'] = options['ignore'] or ['.*', 'terraform']
            options['key'] = options['key'] or f"{app.__module__}-{app.name}/archive.zip"
            if options['api']:
                options['dry'] = True
            dry = options['dry']

            # Transfert zip file to S3 (to be done on each service)
            zip_options = {zip_param.name: options[zip_param.name] for zip_param in zip_command.params}
            ctx.invoke(zip_command, **zip_options)

            # Copy environment files in terraform folder
            config = app.get_config(workspace)
            environment_variable_files = config.existing_environment_variables_files(app)
            for file in environment_variable_files:
                terraform.copy_file(file)

            # Generates common terraform files
            terraform.generate_common_files(**root_command_params, **options)

            # Generates terraform files and copy environment variable files in terraform working dir for provisionning
            terraform_filename = f"{app.name}.{app.ms_type}.tf"
            terraform.generate_files("deploy.j2", terraform_filename, **root_command_params, **options)

            # Apply terraform if not dry
            if not dry:
                terraform.create_stage(**root_command_params, **options)

            # Traces output
            bar.terminate()
            click.echo(f"\nterraform output\n{terraform.output()}")
        except ExitCommand as e:
            bar.terminate(e.msg)
            raise
        except Exception:
            bar.terminate()
            raise


@click.command("deployed", short_help="Retrieve the microservices deployed for this project.")
@click.option('--terraform-dir', default="terraform")
@click.pass_context
@pass_script_info
def deployed_command(info, ctx, terraform_class=TerraformLocal, **options) -> None:
    root_command_params = ctx.find_root().params
    with progressbar(label='Retrieving information', threaded=True) as bar:
        try:
            terraform = terraform_class(info, bar, **root_command_params, **options)
            bar.terminate(f"terraform output : {terraform.output()}")
        except Exception:
            bar.terminate()
            raise

# class CwsTerraformDestroyer(CwsTerraformCommand):


# set all to 0 :
# locals {
#   neorezo-cws_supplier-supplier_order_when_default = var.TFC_WORKSPACE_NAME == "neorezo_cws_supplier" ? 0 : 0
#   neorezo-cws_supplier-supplier_order_when_stage = var.TFC_WORKSPACE_NAME != "neorezo_cws_supplier" ? 0 : 0
# }
# terraform -chdir=terraform_dev apply
# terraform -chdir=terraform apply
# then remove files

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
