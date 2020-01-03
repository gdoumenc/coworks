import os

import boto3

from ..coworks import TechMicroService


class S3MicroService(TechMicroService):
    """ GET http://microservice/bucket/name (key where / are replaced by _)
        Content-Type: application/json"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def aws_access_key_id(self):
        value = os.getenv('AWS_ACCESS_KEY_ID')
        if not value:
            raise EnvironmentError('AWS_ACCESS_KEY_ID not defined in environment')
        return value

    @property
    def aws_secret_access_key(self):
        value = os.getenv('AWS_SECRET_ACCESS_KEY')
        if not value:
            raise EnvironmentError('AWS_SECRET_ACCESS_KEY not defined in environment')
        return value

    def get(self, bucket, key):
        boto_session = boto3.Session(self.aws_access_key_id, self.aws_secret_access_key)
        s3_client = boto_session.client('s3')
        uploaded_object = s3_client.get_object(Bucket=bucket, Key=key.replace('_', '/'))
        return uploaded_object['Body'].read().decode('utf-8')
        # last_modified = uploaded_object['LastModified']
        # print_option = uploaded_object['Metadata'].get('print')
        # cut_option = uploaded_object['Metadata'].get('cut')
        # logger.info("upload done")
        #
        # content = uploaded_object['Body'].read().decode('utf-8')
        # logger.info(f'nesting file key {len(content)}')
