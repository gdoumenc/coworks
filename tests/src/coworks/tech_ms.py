import io
from unittest.mock import MagicMock

from chalice import Response

from coworks import TechMicroService


class TechMS(TechMicroService):
    def __init__(self):
        super().__init__(app_name='test')


class S3MockTechMS(TechMicroService):
    def __init__(self):
        super().__init__(app_name='test')
        session = MagicMock()
        session.client = MagicMock()
        s3_object = {'Body': io.BytesIO(b'test'), 'ContentType': 'text/plain'}
        session.client.get_object = MagicMock(return_value=s3_object)
        self.aws_s3_run_session = session


class SimpleMS(TechMS):

    def get(self):
        """Root access."""
        return "get"

    def get1(self):
        """Not recognized."""
        return "get1"

    def get_content(self):
        return "get content"

    def get__content(self, value):
        return f"get content with {value}"

    def get_content__(self, value, other):
        return f"get content with {value} and {other}"

    def post_content(self, other="none"):
        return f"post content without value but {other}"

    def post_content_(self, value, other="none"):
        return f"post content with {value} and {other}"

    # **param
    def get_kwparam1(self, value=0):
        return f"get **param with only {value}"

    def get_kwparam2(self, value=0, **kwargs):
        return f"get **param with {value} and {list(kwargs.keys())}"

    # composed path
    def get_extended_content(self):
        return "hello world"


class PrefixedMS(TechMS):
    url_prefix = 'prefix'

    def get(self):
        return "hello world"

    def get_content(self):
        return "hello world"

    def get_extended_content(self):
        return "hello world"


class ParamMS(TechMS):
    value = "123"

    def get(self, str):
        return str

    def get_concat(self, str1, str2):
        return str1 + str2

    def get_value(self):
        return self.value

    def put_value(self):
        request = self.current_request
        self.value = request.json_body['value']
        return self.value

    def get_param(self, str1, param1='default1', param2='default2'):
        return str1 + str(param1) + param2


class PrefixedParamMS(TechMS):
    url_prefix = 'prefix'

    def get(self, str):
        return str

    def get_concat(self, str1, str2):
        return str1 + str2


class TupleReturnedMS(TechMS):
    def get(self):
        return 'ok', 200

    def get_resp(self, str):
        return Response(body=str, status_code=200)

    def get_error(self, str):
        return str, 300
