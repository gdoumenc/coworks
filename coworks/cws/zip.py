import base64
import functools
import hashlib
import importlib
import sysconfig
import tempfile
from pathlib import Path
from shutil import copyfile, copytree, ignore_patterns, make_archive

import click

from .command import CwsCommand
from .error import CwsCommandError
from .. import aws


class CwsZipArchiver(CwsCommand):
    """
    This command uploads project source folder as a zip file on a S3 bucket.
    Uploads also the hash code of this file to be able to determined code changes (used by terraform as a trigger).
    """

    @property
    def options(self):
        return [
            *super().options,
            click.option('--bucket', '-b', help="Bucket to upload sources zip file to", required=True),
            click.option('--debug', is_flag=True, help="Print debug logs to stderr."),
            click.option('--dry', is_flag=True, help="Doesn't perform upload."),
            click.option('--hash', is_flag=True, help="Upload also hash code content."),
            click.option('--ignore', '-i', multiple=True, help="Ignore pattern."),
            click.option('--key', '-k', help="Sources zip file bucket's name."),
            click.option('--module_name', '-m', multiple=True, help="Python module added from current pyenv."),
            click.option('--profile_name', '-p', required=True, help="AWS credential profile."),
        ]

    @classmethod
    def multi_execute(cls, project_dir, workspace, execution_list):
        for command, options in execution_list:
            command._zip(**options)

    def __init__(self, app=None, name='zip'):
        super().__init__(app, name=name)

    def _zip(self, *, project_dir, module, bucket, key, profile_name, module_name, hash, dry, debug, ignore, **options):
        aws_s3_session = aws.AwsS3Session(profile_name=profile_name)
        module_name = module_name or []

        key = key if key else f"{module}-{self.app.name}"
        if debug:
            name = f"{module}-{options['service']}"
            where = f"{bucket}/{key}"
            print(f"Uploading zip sources of {name} at s3:{where} {'(not done)' if dry else ''}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            if ignore and type(ignore) is not list:
                ignore = [ignore]
            full_ignore_patterns = functools.partial(ignore_patterns, '*.pyc', '__pycache__', 'bin', 'test', *ignore)

            # Creates archive
            copytree(project_dir, str(tmp_path / 'filtered_dir'),
                     ignore=full_ignore_patterns('*cws.yml', 'env_variables*'))
            for name in module_name:
                if name.endswith(".py"):
                    file_path = Path(sysconfig.get_path('purelib')) / name
                    copyfile(file_path, str(tmp_path / f'filtered_dir/{name}'))
                else:
                    mod = importlib.import_module(name)
                    module_path = Path(mod.__file__).resolve().parent
                    copytree(module_path, str(tmp_path / f'filtered_dir/{name}'), ignore=full_ignore_patterns())
            module_archive = make_archive(str(tmp_path / 'sources'), 'zip', str(tmp_path / 'filtered_dir'))

            # Uploads archive on S3
            with open(module_archive, 'rb') as module_archive:
                b64sha256 = base64.b64encode(hashlib.sha256(module_archive.read()).digest())
                module_archive.seek(0)
                try:
                    if not dry:
                        if debug:
                            print(f"Upload sources...")
                        aws_s3_session.client.upload_fileobj(module_archive, bucket, key)
                        if debug:
                            print(f"Successfully uploaded sources at s3://{bucket}/{key}")
                except Exception as e:
                    print(f"Failed to upload module sources on S3 : {e}")
                    raise CwsCommandError(str(e))

            # Creates hash value
            if hash:
                with tmp_path.with_name('b64sha256_file').open('wb') as b64sha256_file:
                    b64sha256_file.write(b64sha256)

                # Uploads archive hash value to bucket
                with tmp_path.with_name('b64sha256_file').open('rb') as b64sha256_file:
                    try:
                        if not dry:
                            if debug:
                                print(f"Upoad sources hash...")
                            aws_s3_session.client.upload_fileobj(b64sha256_file, bucket, f"{key}.b64sha256",
                                                                 ExtraArgs={'ContentType': 'text/plain'})
                            if debug:
                                print(f"Successfully uploaded sources hash at s3://{bucket}/{key}.b64sha256")
                    except Exception as e:
                        print(f"Failed to upload archive hash on S3 : {e}")
                        raise CwsCommandError(str(e))
