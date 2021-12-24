import base64
import functools
import hashlib
import importlib
import os
import sysconfig
import tempfile
from pathlib import Path
from shutil import copyfile
from shutil import copytree
from shutil import ignore_patterns
from shutil import make_archive

import click
from flask.cli import pass_script_info

from .utils import progressbar
from .. import aws


@click.command("zip", short_help="Zip all source files to create a Lambda file source.")
@click.option('--bucket', '-b', help="Bucket to upload sources zip file to", required=True)
@click.option('--dry', is_flag=True, help="Doesn't perform upload.")
@click.option('--hash', is_flag=True, help="Upload also hash code content.")
@click.option('--ignore', '-i', multiple=True, help="Ignore pattern.")
@click.option('--key', '-k', help="Sources zip file bucket's name.")
@click.option('--module_name', '-m', multiple=True, help="Python module added from current pyenv (module or file.py).")
@click.option('--profile_name', '-p', required=True, help="AWS credential profile.")
@click.pass_context
@pass_script_info
def zip_command(info, ctx, bucket, dry, hash, ignore, module_name, key, profile_name) -> None:
    """
    This command uploads project source folder as a zip file on a S3 bucket.
    Uploads also the hash code of this file to be able to determined code changes (used by terraform as a trigger).
    """
    debug = ctx.find_root().params['debug']
    aws_s3_session = aws.AwsS3Session(profile_name=profile_name)
    module_name = module_name or []

    with progressbar(3, label='Copy files to S3') as bar:
        key = key if key else info.load_app().name
        if debug:
            where = f"{bucket}/{key}"
            bar.echo(f"Uploading zip sources of {info.load_app()} at s3:{where} {'(not done)' if dry else ''}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            if ignore and type(ignore) is not list:
                if type(ignore) is tuple:
                    ignore = [*ignore]
                else:
                    ignore = [ignore]
            ignore = [*ignore, '*.pyc', '__pycache__']
            ignore = [*ignore, 'Pipfile*', 'requirements.txt']
            full_ignore_patterns = functools.partial(ignore_patterns, *ignore)

            # Creates archive
            project_dir = ctx.find_root().params.get('project_dir')
            full_project_dir = Path(project_dir).resolve()
            try:
                if tmp_path.relative_to(full_project_dir):
                    msg = f"Cannot deploy a project defined in tmp folder (project dir id {full_project_dir})"
                    raise click.exceptions.UsageError(msg)
            except (Exception,):
                pass

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
            bar.update(msg=f"Sources is {int(os.path.getsize(module_archive) / 1000)} Kb" if debug else "")

            # Uploads archive on S3
            if not dry:
                with open(module_archive, 'rb') as archive:
                    b64sha256 = base64.b64encode(hashlib.sha256(archive.read()).digest())
                    archive.seek(0)
                    try:
                        aws_s3_session.client.upload_fileobj(archive, bucket, key)
                    except Exception as e:
                        bar.echo(f"Failed to upload module sources on S3 : {e}")
                        raise e
                bar.update(msg=f"Successfully uploaded sources at s3://{bucket}/{key}" if debug else "")

            # Creates hash value
            if not dry:
                if hash:
                    with tmp_path.with_name('b64sha256_file').open('wb') as b64sha256_file:
                        b64sha256_file.write(b64sha256)

                    # Uploads archive hash value to bucket
                    with tmp_path.with_name('b64sha256_file').open('rb') as b64sha256_file:
                        try:
                            aws_s3_session.client.upload_fileobj(b64sha256_file, bucket, f"{key}.b64sha256",
                                                                 ExtraArgs={'ContentType': 'text/plain'})
                        except Exception as e:
                            bar.echo(f"Failed to upload archive hash on S3 : {e}")
                            raise e

                msg = f"Successfully uploaded sources hash at s3://{bucket}/{key}.b64sha256"
                bar.update(msg=msg if debug and not dry else "")
