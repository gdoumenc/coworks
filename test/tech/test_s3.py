import os

import requests
import pytest

from coworks.tech import S3MicroService

TEST_BUCKET = "cowoks-s3-pytest"
TEST_KEY = "key/test/coworks"


@pytest.mark.tech
class TestS3Class:

    def test_list_buckets(self, local_server_factory):
        assert os.getenv('AWS_ACCESS_KEY_ID') is not None, \
            "You must define AWS_ACCESS_KEY_ID in environment variable for testing"
        assert os.getenv('AWS_SECRET_ACCESS_KEY') is not None, \
            "You must define AWS_SECRET_ACCESS_KEY in environment variable for testing"
        assert os.getenv('AWS_REGION') is not None, \
            "You must define AWS_REGION in environment variable for testing"
        local_server = local_server_factory(S3MicroService())

        # delete any case : even not here as may also be created because previous test failed
        local_server.make_call(requests.delete, f'/bucket/{TEST_BUCKET}', timeout=10)

        # get list
        response = local_server.make_call(requests.get, '/buckets', timeout=10)
        assert response.status_code == 200
        assert 'Buckets' in response.json()
        names = [b['Name'] for b in response.json()['Buckets']]
        assert TEST_BUCKET not in names

    def test_create_delete_bucket(self, local_server_factory):
        local_server = local_server_factory(S3MicroService())

        # create bucket
        response = local_server.make_call(requests.put, f'/bucket/{TEST_BUCKET}', timeout=10)
        assert response.status_code == 200
        response = local_server.make_call(requests.get, f'/bucket/{TEST_BUCKET}', timeout=10)
        assert response.status_code == 200
        assert response.json()['Name'] == TEST_BUCKET

        # cannot recreate
        response = local_server.make_call(requests.put, f'/bucket/{TEST_BUCKET}', timeout=10,
                                          params={'key': TEST_KEY, 'body': b"test"})
        assert response.status_code == 200
        response = local_server.make_call(requests.get, f'/content/{TEST_BUCKET}', timeout=10,
                                          params={'key': TEST_KEY})
        assert response.status_code == 200
        assert response.text == "test"
        response = local_server.make_call(requests.delete, f'/bucket/{TEST_BUCKET}', timeout=10,
                                          params={'key': TEST_KEY})
        assert response.status_code == 200

        # create key
        response = local_server.make_call(requests.get, f'/bucket/{TEST_BUCKET}', timeout=10)
        assert response.status_code == 200

        # delete
        response = local_server.make_call(requests.delete, f'/bucket/{TEST_BUCKET}', timeout=10)
        assert response.status_code == 200
