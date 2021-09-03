import json
import requests

from coworks import TechMicroService
from coworks import entry


class ContentMS(TechMicroService):

    @entry
    def get(self):
        return "test"

    @entry
    def get_json(self):
        return {'text': 'value', 'int': 1}

    @entry
    def post(self, text=None, context=None, files=None):
        if files:
            if type(files) is not list:
                files = [files]
            return f"post {text}, {context} and {[f.file.name for f in files]}"
        return f"post {text}, {context}"


# session = MagicMock()
# session.client = MagicMock()
# s3_object = {'Body': io.BytesIO(b'test'), 'ContentType': 'text/plain'}
# session.client.get_object = MagicMock(return_value=s3_object)


import pytest


class TestClass:

    def test_text_api(self):
        app = ContentMS()
        with app.test_client() as c:
            headers = {'Authorization': 'token'}
            response = c.get('/', headers=headers)
            assert response.status_code == 200
            assert response.is_json
            assert response.get_data(as_text=True) == 'test'

            headers = {'Accept': 'application/json', 'Authorization': 'token'}
            response = c.get('/', headers=headers)
            assert response.status_code == 200
            assert response.is_json
            assert response.get_data(as_text=True) == 'test'

            headers = {'Accept': 'text/plain', 'Authorization': 'token'}
            response = c.get('/', headers=headers)
            assert response.status_code == 200
            assert not response.is_json
            assert response.get_data(as_text=True) == 'test'

            # headers = {'Authorization': 'token'}
            # response = c.get('/json', headers=headers)
            # assert response.status_code == 200
            # assert response.get_data(as_text=True) == {"int":1,"text":"value"}

    @pytest.mark.skip
    def test_text_plain(self, local_server_factory):
        """normal API call."""
        tech = TechMS()
        local_server = local_server_factory(tech)
        data = json.dumps({'text': 'value'})
        headers = {'Content-type': 'text/plain'}
        response = local_server.make_call(requests.post, '/params', data=data, timeout=500, headers=headers)
        assert response.status_code == 200

    @pytest.mark.skip
    def test_form_data(self, local_server_factory):
        """normal API call."""
        tech = TechMS()
        tech.aws_s3_form_data_session = session
        local_server = local_server_factory(tech)
        data = {'key': 'value'}
        multiple_files = [
            ('text', (None, "hello world")),
            ('context', (None, json.dumps(data), 'application/json')),
            ('files', ('f1.csv', 'some,data,to,send\nanother,row,to,send\n')),
            ('files', ('f2.txt', 'some,data,to,send\nanother,row,to,send\n', 'text/plain')),
            ('files', ('f3.j2', 'bucket/key', 'text/s3')),
        ]
        response = local_server.make_call(requests.post, '/params', files=multiple_files, json=data)
        assert response.status_code == 200
        assert response.text == "post hello world, {'key': 'value'} and ['f1.csv', 'f2.txt', 'f3.j2']"
