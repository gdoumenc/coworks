import io
from unittest.mock import MagicMock

from chalice import Response

from coworks import TechMicroService, entry


class TechMS(TechMicroService):
    def __init__(self, **kwargs):
        super().__init__(name='test', **kwargs)


class S3MockTechMS(TechMicroService):
    def __init__(self):
        super().__init__(name='test')
        session = MagicMock()
        session.client = MagicMock()
        s3_object = {'Body': io.BytesIO(b'test'), 'ContentType': 'text/plain'}
        session.client.get_object = MagicMock(return_value=s3_object)
        self.aws_s3_run_session = session


class SimpleMS(TechMS):

    @entry
    def get(self):
        """Root access."""
        return "get"

    def get1(self):
        """Not recognized."""
        return "get1"

    @entry
    def get_content(self):
        return "get content"

    @entry
    def get__content(self, value):
        return f"get content with {value}"

    @entry
    def get_content__(self, value, other):
        return f"get content with {value} and {other}"

    @entry
    def post_content(self, other="none"):
        return f"post content without value but {other}"

    @entry
    def post_content_(self, value, other="none"):
        return f"post content with {value} and {other}"

    # **param
    @entry
    def get_kwparam1(self, value=0):
        return f"get **param with only {value}"

    @entry
    def get_kwparam2(self, value=0, **kwargs):
        return f"get **param with {value} and {list(kwargs.keys())}"

    # composed path
    @entry
    def get_extended_content(self):
        return "hello world"


class ParamMS(TechMS):
    value = "123"

    @entry
    def get(self, str):
        return str

    @entry
    def get_concat(self, str1, str2):
        return str1 + str2

    @entry
    def get_value(self):
        return self.value

    @entry
    def put_value(self, value=None):
        self.value = value
        return self.value

    @entry
    def get_param(self, str1, param1='default1', param2='default2'):
        return str1 + str(param1) + param2


class TupleReturnedMS(TechMS):
    @entry
    def get(self):
        return 'ok', 200

    @entry
    def get_json(self):
        return {'value': 'ok'}, 200

    @entry
    def get_resp(self, str):
        return Response(body=str, status_code=200)

    @entry
    def get_error(self, str):
        return str, 300

    @entry
    def get_tuple(self, str):
        return (str, 200, {'x-test': 'true'})
