import pytest
import requests

# from coworks.tech.s3 import S3MicroService

env = {
    "AWS_ACCESS_KEY_ID": "access key",
    "AWS_SECRET_ACCESS_KEY": "secret key",
    "AWS_REGION": "region"
}


# class S3Test(S3MicroService):
#
#     def __init__(self, client, **kwargs):
#         super().__init__(**kwargs)
#         self.__s3_client__ = client
#
#
# @pytest.mark.local
# class NotDoneTestS3Class:
#
#     def test_list_buckets(self, local_server_factory, boto3_mock_fixture):
#         local_server = local_server_factory(S3Test(boto3_mock_fixture, env=env))
#
#         # get list
#         response = local_server.make_call(requests.get, '/bucket')
#         assert response.status_code == 200
#         assert 'Buckets' in response.json()
#         names = [b['Name'] for b in response.json()['Buckets']]
#         assert "bucket" in names
#
#     def test_create_delete_bucket(self, local_server_factory, boto3_mock_fixture):
#         local_server = local_server_factory(S3Test(boto3_mock_fixture, env=env))
#
#         # existing bucket
#         response = local_server.make_call(requests.get, '/bucket/bucket')
#         assert response.status_code == 200
#         response = local_server.make_call(requests.get, '/bucket/test')
#         assert response.status_code == 404
#
#         # creates bucket
#         response = local_server.make_call(requests.put, '/bucket/test')
#         assert response.status_code == 200
#         boto3_mock_fixture.create_bucket.assert_called_once_with(bucket='test',
#                                                                  createBucketConfiguration={'LocationConstraint': 'EU'})
#         response = local_server.make_call(requests.get, '/bucket/test')
#         assert response.status_code == 200
#         assert response.json()['Name'] == "test"
#         boto3_mock_fixture.list_objects.assert_called_with(bucket='test')
#
#         # cannot recreate
#         response = local_server.make_call(requests.put, '/bucket/test')
#         assert response.status_code == 400
#
#         # creates key
#         response = local_server.make_call(requests.get, '/bucket/test', params={'key': 'key'})
#         assert response.status_code == 404
#         response = local_server.make_call(requests.put, '/content/test', params={'key': 'key', 'body': "content"})
#         assert response.status_code == 200
#         boto3_mock_fixture.put_object.assert_called_once_with(bucket='test', key='key', body='content')
#         response = local_server.make_call(requests.get, '/bucket/test', params={'key': 'key'})
#         assert response.status_code == 200
#         response = local_server.make_call(requests.get, '/content/test', params={'key': 'key'})
#         assert response.status_code == 200
#         assert response.text == "content"
#
#         # delete bucket
#         response = local_server.make_call(requests.delete, '/bucket/test')
#         assert response.status_code == 200
#         response = local_server.make_call(requests.get, '/bucket/test')
#         assert response.status_code == 404
