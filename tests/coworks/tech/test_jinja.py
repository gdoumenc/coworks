import json
import requests
import tempfile
import urllib.parse


import pytest
@pytest.mark.skip
class TestClass:

    def test_render_template_in_url(self, local_server_factory):
        local_server = local_server_factory(JinjaRenderMicroService(configs=LocalConfig()))
        template = urllib.parse.quote_plus("hello {{ world_name }}")
        response = local_server.make_call(requests.get, f"/render/{template}", params={'world_name': 'world'})
        assert response.status_code == 200
        assert response.json() == {"render": "hello [\'world\']"}

    def test_render_template_multipart_form(self, local_server_factory):
        local_server = local_server_factory(JinjaRenderMicroService(configs=LocalConfig()))

        template = tempfile.TemporaryFile()
        template.write("hello {{ world_name }}".encode())
        template.seek(0)

        context = tempfile.TemporaryFile()
        context.write(json.dumps({"world_name": "the world"}).encode())
        context.seek(0)

        response = local_server.make_call(requests.post, "/render/template.jinja",
                                          files={'templates': ('template.jinja', template, 'text/plain'),
                                                 'context': (None, context, 'application/json')})
        assert response.status_code == 200
        assert response.json() == {"render": "hello the world"}
