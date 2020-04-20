import cgi
import inspect
import io
import json

from aws_xray_sdk.core import xray_recorder
from chalice import BadRequestError

from .mixins import Boto3Mixin


class BotoSession(Boto3Mixin):

    @staticmethod
    def client(service):
        return BotoSession().boto3_session.client(service)


class FileParam:

    def __init__(self, file, mime_type):
        self.file = file
        self.mime_type = mime_type

    def __repr__(self):
        if self.mime_type:
            return f'FileParam({self.file.name}, {self.mime_type})'
        return f'FileParam({self.file.name})'


def class_auth_methods(obj):
    """Returns the auth method from the class if exists."""
    methods = inspect.getmembers(obj.__class__, lambda x: inspect.isfunction(x))

    for name, func in methods:
        if name == 'auth':
            return func
    return None


def class_rest_methods(obj):
    """Returns the list of methods from the class."""
    methods = inspect.getmembers(obj.__class__, lambda x: inspect.isfunction(x))

    res = []
    for name, func in methods:
        if name == 'get' or name.startswith('get_'):
            res.append(('get', func))
        elif name.startswith('post'):
            res.append(('post', func))
        elif name.startswith('put'):
            res.append(('put', func))
        elif name.startswith('delete'):
            res.append(('delete', func))
        elif name.startswith('patch'):
            res.append(('patch', func))
    return res


def class_attribute(obj, name: str = None, defaut=None):
    """Returns the list of attributes from the class or the attribute if name parameter is defined
    or default value if not found."""
    attributes = inspect.getmembers(obj.__class__, lambda x: not inspect.isroutine(x))

    if not name:
        return attributes

    filtered = [a[1] for a in attributes if a[0] == name]
    return filtered[0] if filtered else defaut


def trim_underscores(name):
    while name.startswith('_'):
        name = name[1:]
    while name.endswith('_'):
        name = name[:-1]
    return name


def begin_xray_subsegment(subsegment_name):
    if xray_recorder.in_segment().segment is not None:
        return xray_recorder.begin_subsegment(subsegment_name)
    return None


def end_xray_subsegment():
    if xray_recorder.in_subsegment().subsegment is not None:
        return xray_recorder.end_subsegment()


def get_multipart_content(part):
    headers = {k.decode('utf-8'): cgi.parse_header(v.decode('utf-8')) for k, v in part.headers.items()}
    content = part.content
    _, content_disposition_params = headers['Content-Disposition']
    part_content_type, _ = headers.get('Content-Type', (None, None))
    name = content_disposition_params['name']

    # content in a text or json value
    if 'filename' not in content_disposition_params:
        if part_content_type == 'application/json':
            return name, json.loads(content.decode('utf-8'))
        return name, content.decode('utf-8')

    # content in a file (s3 or plain text)
    if part_content_type == 'text/s3':
        pathes = content.decode('utf-8').split('/', 1)
        client = BotoSession.client('s3')
        try:
            s3_object = client.get_object(Bucket=pathes[0], Key=pathes[1])
        except:
            print(f"Bucket={pathes[0]} Key={pathes[1]} not found on s3")
            return BadRequestError(f"Bucket={pathes[0]} Key={pathes[1]} not found on s3")
        file = io.BytesIO(s3_object['Body'].read())
        mime_type = s3_object['ContentType']
    else:
        file = io.BytesIO(content)
        mime_type = part_content_type
    file.name = content_disposition_params['filename']

    return name, FileParam(file, mime_type)


def set_multipart_content(form_data):
    def encode_part(_part):
        mime_type = _part.get('mime_type', 'text/plain')
        filename = _part.get('filename')
        if mime_type == 'text/plain':
            content = _part.get('content')
            return filename, content, mime_type
        elif mime_type == 'application/json':
            content = _part.get('content')
            return filename, json.dumps(content), mime_type
        elif mime_type == 'text/s3':
            path = _part.get('path')
            return filename, path, mime_type
        else:
            raise BadRequestError(f"Undefined mime type {mime_type}")

    parts = []
    for name, part in form_data.items():
        if type(part) is list:
            parts.extend([(name, encode_part(p)) for p in part])
        else:
            parts.append((name, encode_part(part)))
    return parts
