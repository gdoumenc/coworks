import requests
import urllib.parse
from coworks.tech import JinjaRenderMicroservice


def test_send(local_server_factory, email_mock_fixture):
    local_server = local_server_factory(JinjaRenderMicroservice())
    template = urllib.parse.quote_plus("hello {{ world_name }}")
    response = local_server.make_call(requests.get, f"/render/{template}", params={'world_name': 'world'})
    assert response.status_code == 200
    assert response.text == "hello world"
