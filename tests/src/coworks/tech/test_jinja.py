import requests
import json
import os
import urllib.parse
from coworks.tech import JinjaRenderMicroService


def test_render_template_in_url(local_server_factory):
    local_server = local_server_factory(JinjaRenderMicroService())
    template = urllib.parse.quote_plus("hello {{ world_name }}")
    response = local_server.make_call(requests.get, f"/render/{template}", params={'world_name': 'world'})
    assert response.status_code == 200
    assert response.json() == {"render": "hello [\'world\']"}


def test_render_template_multipart_form(local_server_factory):
    local_server = local_server_factory(JinjaRenderMicroService())

    template = open("template.jinja", "w+")
    template.write("hello {{ world_name }}")
    template.close()

    context = open("context.json", "w+")
    context.write(json.dumps({"world_name": "the world"}))
    context.close()

    template = open("template.jinja", "r")
    context = open("context.json", "r")

    response = local_server.make_call(requests.post, f"/render/template.jinja",
                                      files={'templates': ('template.jinja', template, 'text/plain'),
                                             'context': (None, context, 'application/json')})
    assert response.status_code == 200
    assert response.json() == {"render": "hello the world"}
    os.remove("template.jinja")
