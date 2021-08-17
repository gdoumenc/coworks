# import logging
# import subprocess
# from abc import ABC
# from dataclasses import dataclass
# from pathlib import Path
# from shutil import copy
# from subprocess import CalledProcessError
# from threading import Thread
# from typing import Optional, Dict
#
# import boto3
# import click
# import itertools
# import sys
# from time import sleep
#
# from coworks.aws import AwsS3Session
# from coworks.coworks import Entry
#
# UID_SEP = '_'
#
# logging.getLogger("python_terraform").setLevel(logging.ERROR)
#
#
# class Terraform:
#
#     def __init__(self, working_dir='terraform', timeout=240):
#         self.working_dir = working_dir
#         Path(self.working_dir).mkdir(exist_ok=True)
#         self.timeout = timeout
#
#     def init(self):
#         self.__execute(['init', '-input=false'])
#
#     def apply(self, workspace):
#         self.select_workspace(workspace)
#         self.__execute(['apply', '-auto-approve', '-parallelism=1'])
#
#     def destroy(self, workspace):
#         self.select_workspace(workspace)
#         self.__execute(['apply', '-destroy', '-auto-approve', '-parallelism=1'])
#         if workspace != "default":
#             self.__execute(['workspace', 'delete', workspace])
#
#     def output(self):
#         self.select_workspace("default")
#         values = self.__execute(['output']).stdout
#         return values.decode("utf-8").strip()
#
#     def workspace_list(self):
#         self.select_workspace("default")
#         values = self.__execute(['workspace', 'list']).stdout
#         values = values[1:].decode("utf-8").split('\n')
#         return [w.strip() for w in filter(None, values)]
#
#     def select_workspace(self, workspace):
#         if not (Path(self.working_dir) / '.terraform').exists():
#             self.init()
#         try:
#             self.__execute(["workspace", "select", workspace])
#         except CwsCommandError:
#             self.__execute(["workspace", "new", workspace])
#
#     def __execute(self, cmds):
#         p = subprocess.run(["terraform", *cmds], capture_output=True, cwd=self.working_dir, timeout=self.timeout)
#         try:
#             p.check_returncode()
#             return p
#         except CalledProcessError:
#             raise CwsCommandError(p.stderr.decode("utf-8"))
#
#
# @dataclass
# class TerraformResource:
#     parent_uid: str
#     path: str
#     entries: Dict[str, Entry]
#     cors: CORSConfig
#
#     @property
#     def uid(self):
#         def remove_brackets(path):
#             return f"{path.replace('{', '').replace('}', '')}"
#
#         if self.path is None:
#             return ''
#
#         last = remove_brackets(self.path)
#         return f"{self.parent_uid}{UID_SEP}{last}" if self.parent_uid else last
#
#     @property
#     def is_root(self):
#         return self.path is None
#
#     @property
#     def parent_is_root(self):
#         return self.parent_uid == ''
#
#     def __repr__(self):
#         return f"{self.uid}:{self.entries}"
#
#
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
