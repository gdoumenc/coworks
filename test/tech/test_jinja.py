import requests
import os
import urllib.parse
from coworks.tech import JinjaRenderMicroservice


def test_render_template_in_url(local_server_factory):
    local_server = local_server_factory(JinjaRenderMicroservice())
    template = urllib.parse.quote_plus("hello {{ world_name }}")
    response = local_server.make_call(requests.get, f"/render/{template}", params={'world_name': 'world'})
    assert response.status_code == 200
    assert response.json() == {"render": "hello [\'world\']"}


def test_render_template_multipart_form(local_server_factory):
    local_server = local_server_factory(JinjaRenderMicroservice())
    template = open("template.jinja", "w+")
    template.write("hello {{ world_name }}")
    template.close()
    template = open("template.jinja", "r")
    response = local_server.make_call(requests.post, f"/render/template.jinja",
                                      params={'world_name': 'world'},
                                      files={'file': ('template.jinja', template, 'text/plain')})
    assert response.status_code == 200
    assert response.json() == {"render": "hello [\'world\']"}
    os.remove("template.jinja")
