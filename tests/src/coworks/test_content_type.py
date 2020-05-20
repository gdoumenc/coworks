import io
import json
from unittest.mock import MagicMock

import requests

from coworks import TechMicroService
from coworks.cws.writer.sfn import TechState


class TechMS(TechMicroService):
    def __init__(self):
        super().__init__(app_name='test')

    def post_params(self, text=None, context=None, files=None):
        if files:
            if type(files) is not list:
                files = [files]
            return f"post {text}, {context} and {[f.file.name for f in files]}"
        return f"post {text}, {context}"


session = MagicMock()
session.client = MagicMock()
s3_object = {'Body': io.BytesIO(b'test'), 'ContentType': 'text/plain'}
session.client.get_object = MagicMock(return_value=s3_object)


def test_text_plain(local_server_factory):
    """normal API call."""
    tech = TechMS()
    local_server = local_server_factory(tech)
    data = json.dumps({'text': 'value'})
    headers = {'Content-type': 'text/plain'}
    response = local_server.make_call(requests.post, '/params', data=data, timeout=500, headers=headers)
    assert response.status_code == 415


def test_form_data(local_server_factory):
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


def test_sfn_arg_params():
    """step function call."""
    tech = TechMS()
    tech.aws_s3_form_data_session = session
    form_data = {
        'text': {'content': "hello world"},
        'context': {'content': {'key': 'value'}, 'mime_type': 'application/json'},
        'files': [
            {'filename': 'f1.csv', 'content': 'some,data', 'mime_type': 'text/plain'},
            {'filename': 'f2.txt', 'content': 'content2', 'mime_type': 'text/plain'},
            {'filename': 'f3.j2', 'path': 'bucket/key', 'mime_type': 'text/s3'},
        ],
    }
    data = {'post': '/params', 'form-data': form_data}
    call = TechState.get_call_data(None, data)
    response = tech(call, {})
    assert response['statusCode'] == 200
    assert response['body'] == "post hello world, {'key': 'value'} and ['f1.csv', 'f2.txt', 'f3.j2']"


def test_sfn_simple_arg_params():
    """simplified step function call."""
    tech = TechMS()
    tech.aws_s3_form_data_session = session
    form_data = {
        'text': "hello world",
        'context': {'json': True},
        'files': {'s3': 'bucket/key'},
    }
    data = {'post': '/params', 'form-data': form_data}
    call = TechState.get_call_data(None, data)
    response = tech(call, {})
    assert response['statusCode'] == 200
    assert response['body'] == "post hello world, True and ['key']"
