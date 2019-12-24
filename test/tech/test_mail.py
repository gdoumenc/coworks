from collections import defaultdict
import requests

from coworks.tech import MailMicroService


env = {
    'smtp_server': 'mail.test',
    'to' : [],
    'subject' : "Test mail"
}


# def test_simple_example(local_server_factory):
#     local_server = local_server_factory(MailMicroService(env=env))
#     response = local_server.make_call(requests.post, '/')
#     assert response.status_code == 200
#     assert response.text == "Mail sent"
