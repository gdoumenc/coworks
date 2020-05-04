from unittest.mock import MagicMock

import pytest

from coworks import TechMicroService

client = MagicMock()
session = MagicMock()
session.client = client


class TechMS(TechMicroService):

    def get_test(self):
        return "get"


class LambdaContext:

    def __init__(self):
        self.aws_request_id = "id"
        self.function_name = "fun"


def test_save_on_s3():
    data = {
        'short': "normal",
        'long': "x" * 10000,
    }
    tech: TechMS = TechMS()
    tech.aws_s3_sfn_data_session = session
    tech.lambda_context = LambdaContext()
    res = tech._set_data_on_s3(data)
    client.put_object.assert_called()
    assert res['short'] == 'normal'
    assert res['long'].startswith('$$')
    assert res['long'].endswith('$$')
