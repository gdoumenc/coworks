import json
import os

import boto3

from chalice import BadRequestError, NotFoundError
from ..coworks import TechMicroService


class S3MicroService(TechMicroService):
    """ GET http://microservice/bucket/name (key where / are replaced by _)
        Content-Type: application/json"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__s3_client__ = None

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

    @property
    def region_name(self):
        value = os.getenv('AWS_REGION')
        if not value:
            raise EnvironmentError('AWS_REGION not defined in environment')
        return value

    @property
    def s3_client(self):
        if self.__s3_client__ is None:
            boto_session = boto3.Session(self.aws_access_key_id, self.aws_secret_access_key,
                                         region_name=self.region_name)
            self.__s3_client__ = boto_session.client('s3')
        return self.__s3_client__

    def get_bucket(self):
        """Return the list buckets defined."""
        return json.dumps(self.s3_client.list_buckets(), indent=4, sort_keys=True, default=str)

    def get_bucket_(self, bucket, key=None):
        """Returns an object in the bucket from the key or the list of objects contained in the bucket."""
        if key:
            uploaded_object = self.s3_client.get_object(bucket=bucket, key=key)
            if not uploaded_object:
                raise NotFoundError(f"No key '{key}' in bucket '{bucket}'")
            return uploaded_object["Name"]
        else:
            b = self.s3_client.list_objects(bucket=bucket)
            if b is None:
                raise NotFoundError(f"No  bucket '{bucket}'")
            return {'Name': bucket}

    def put_bucket(self, bucket):
        kwargs = {}
        found = self.s3_client.list_objects(bucket=bucket)
        if found is not None:
            raise BadRequestError(f"Bucket '{bucket}' already exists.")
        if self.region_name != 'us-east-1':
            kwargs['createBucketConfiguration'] = {'LocationConstraint': 'EU'}
        self.s3_client.create_bucket(bucket=bucket, **kwargs)

    def delete_bucket(self, bucket, key=None):
        if key is None:
            self.s3_client.delete_bucket(bucket=bucket)
        else:
            self.s3_client.delete_object(bucket=bucket, key=key)

    def get_content(self, bucket, key=None):
        if key:
            uploaded_object = self.s3_client.get_object(bucket=bucket, key=key)
            if not uploaded_object:
                return NotFoundError(f"No key '{key}' in bucket '{bucket}'")
            return uploaded_object['Body'].read().decode('utf-8')
        else:
            raise BadRequestError("Key is missing.")

    def put_content(self, bucket, key=None, body=b''):
        if key:
            self.s3_client.put_object(bucket=bucket, key=key, body=body)
        else:
            raise BadRequestError("Key is missing.")
