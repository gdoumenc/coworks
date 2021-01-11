import json

from chalice import BadRequestError, NotFoundError

from ..coworks import TechMicroService, aws


class S3MicroService(aws.Boto3Mixin, TechMicroService):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__s3_client__ = None

    @property
    def s3_client(self):
        if self.__s3_client__ is None:
            self.__s3_client__ = self.boto3_session.client('s3')
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
