import shutil
import click
import tempfile
import os
import base64
import hashlib

from .command import CwsCommand
from coworks.mixins import Boto3Mixin, AwsS3Session


class CwsZipArchiver(CwsCommand, Boto3Mixin):
    def __init__(self, app=None, name='zip'):
        super().__init__(app, name=name)

    @property
    def options(self):
        return (
            click.option('--bucket', '-b', help='Bucket to upload zip to'),
            click.option('--debug/--no-debug', default=False, help='Print debug logs to stderr.')
        )

    def _execute(self, *, module, service, project_dir, bucket, debug=True, **kwargs):
        aws_s3_session = AwsS3Session(profile_name='fpr-customer')

        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_archive = os.path.join(temp_dir, 'archive')
            tmp_archive = shutil.make_archive(tmp_archive, 'zip', project_dir)
            tmp_archive = open(tmp_archive, 'rb')

            b64sha256 = base64.b64encode(hashlib.sha256(tmp_archive.read()).digest())
            tmp_archive.seek(0)
            print(b64sha256)

            b64sha256_file = open(os.path.join(temp_dir, 'b64sha256_file'), 'wb')
            b64sha256_file.write(b64sha256)
            b64sha256_file.close()
            b64sha256_file = open(os.path.join(temp_dir, 'b64sha256_file'), 'rb')

            archive_name = f"source_archives/{module}-{service}/archive.zip"
            try:
                aws_s3_session.client.upload_fileobj(tmp_archive, bucket, archive_name)
                aws_s3_session.client.upload_fileobj(b64sha256_file, bucket, f"{archive_name}.b64sha256",
                                                     ExtraArgs={'ContentType': 'text/plain'})
            except Exception as e:
                print(e)
            finally:
                tmp_archive.close()
                b64sha256_file.close()

