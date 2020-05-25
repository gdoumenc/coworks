import smtplib
from email import message
from unittest.mock import Mock, MagicMock

#
# Email
#

email_mock = message.EmailMessage()
email_mock.set_content = Mock()
email_mock.add_attachment = Mock()


class EmailMessageMock:
    def __new__(cls, *args, **kwargs):
        return email_mock


message.EmailMessage = EmailMessageMock

smtp_mock = MagicMock()
smtp_mock.__enter__.return_value = smtp_mock
smtp_mock.send_message.return_value = "Mail sent to you@test.com"


class SMTPMock:
    def __new__(cls, *args, **kwargs):
        return smtp_mock


smtplib.SMTP = SMTPMock

#
# S3
#

boto3_mock = MagicMock()


class S3Reader():

    def __init__(self, content):
        self.content = content

    def read(self):
        return self.content.encode()

    def write(self, content):
        self.content = content


class BucketMockup:
    BUCKETS = {'bucket': {'key': S3Reader('content')}}

    @classmethod
    def add_bucket(cls, bucket='', **kwargs):
        cls.BUCKETS[bucket] = {}

    @classmethod
    def get_bucket(cls, bucket=''):
        return cls.BUCKETS.get(bucket)

    @classmethod
    def delete_bucket(cls, bucket=''):
        del cls.BUCKETS[bucket]

    @classmethod
    def get_list(cls):
        return {"Buckets": [{'Name': k} for k in cls.BUCKETS]}

    @classmethod
    def get_object(cls, bucket='', key=''):
        buck = cls.get_bucket(bucket)
        return {"Body": buck.get(key), "Name": key} if key in buck else {}

    @classmethod
    def put_content(cls, bucket='', key='', body=''):
        obj = cls.get_object(bucket)
        if obj:
            obj["Body"].write(body)
        else:
            cls.get_bucket(bucket)[key] = S3Reader(body)


boto3_mock.list_buckets = Mock(side_effect=BucketMockup.get_list)
boto3_mock.list_objects = Mock(side_effect=BucketMockup.get_bucket)

boto3_mock.create_bucket = Mock(side_effect=BucketMockup.add_bucket)
boto3_mock.delete_object.return_value = {"Buckets": [{"Name": 'bucket'}]}
boto3_mock.delete_bucket = Mock(side_effect=BucketMockup.delete_bucket)

boto3_mock.get_object = Mock(side_effect=BucketMockup.get_object)
boto3_mock.put_object = Mock(side_effect=BucketMockup.put_content)
# boto3_mock.delete_object = Mock(side_effect=s3_delete)
