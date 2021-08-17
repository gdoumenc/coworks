import io
from unittest.mock import MagicMock

from coworks import TechMicroService, entry
from coworks.config import LocalConfig


class TechMS(TechMicroService):
    def __init__(self, configs=None, **kwargs):
        super().__init__('test', configs=configs or LocalConfig(), **kwargs)


class S3MockTechMS(TechMicroService):
    def __init__(self):
        super().__init__('test')
        session = MagicMock()
        session.client = MagicMock()
        s3_object = {'Body': io.BytesIO(b'test'), 'ContentType': 'text/plain'}
        session.client.get_object = MagicMock(return_value=s3_object)
        self.aws_s3_run_session = session


class SimpleMS(TechMicroService):

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

    @entry
    def put_kwparam2_(self, value=0, **kwargs):
        return f"get **param with {value} and {list(kwargs.keys())}"

    # composed path
    @entry
    def get_extended_content(self):
        return "hello world"

