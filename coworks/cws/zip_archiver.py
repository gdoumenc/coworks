import base64
import hashlib
import tempfile
from pathlib import Path
from shutil import copytree, ignore_patterns, make_archive

import click
from coworks.cws.error import CwsCommandError
from coworks.mixins import Boto3Mixin, AwsS3Session

from .command import CwsCommand


class CwsZipArchiver(CwsCommand, Boto3Mixin):
    def __init__(self, app=None, name='zip'):
        super().__init__(app, name=name)

    @property
    def options(self):
        return [
            *super().options,
            click.option('--customer', '-c'),
            click.option('--profile_name', '-p'),
            click.option('--bucket', '-b', help='Bucket to upload zip to'),
            click.option('--debug/--no-debug', default=False, help='Print debug logs to stderr.')
        ]

    def _execute(self, options):
        if options['bucket'] is None:
            raise CwsCommandError("Undefined bucket (option -b must be defined).\n")
        aws_s3_session = AwsS3Session(profile_name=options['profile_name'])

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            copytree(options.project_dir, str(tmp_path.with_name('filtered_dir')),
                     ignore=ignore_patterns('__pycache__*'))
            module_archive = make_archive(str(tmp_path.with_name('archive')), 'zip',
                                          str(tmp_path.with_name('filtered_dir')))
            with open(module_archive, 'rb') as module_archive:
                b64sha256 = base64.b64encode(hashlib.sha256(module_archive.read()).digest())
                module_archive.seek(0)
                try:
                    archive_name = f"source_archives/{options.module}-{options.service}-{options['customer']}/archive.zip"
                    aws_s3_session.client.upload_fileobj(module_archive, options['bucket'], archive_name)
                    print(f"Successfully uploaded archive as {archive_name} ")
                except Exception as e:
                    print(f"Failed to upload module archive on S3 : {e}")
                    raise CwsCommandError(str(e))

            with tmp_path.with_name('b64sha256_file').open('wb') as b64sha256_file:
                b64sha256_file.write(b64sha256)

            with tmp_path.with_name('b64sha256_file').open('rb') as b64sha256_file:
                try:
                    aws_s3_session.client.upload_fileobj(b64sha256_file, options['bucket'], f"{archive_name}.b64sha256",
                                                         ExtraArgs={'ContentType': 'text/plain'})
                    print(
                        f"Successfully uploaded archive hash as {archive_name}.b64sha256, value of the hash : {b64sha256} ")
                except Exception as e:
                    print(f"Failed to upload archive hash on S3 : {e}")
                    raise CwsCommandError(str(e))
