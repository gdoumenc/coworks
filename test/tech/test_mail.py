import requests
import smtplib
from unittest.mock import MagicMock, patch

from coworks.tech import MailMicroService

env = {
    "SMTP_SERVER": "mail.test.com:587",
    "SMTP_LOGIN": "myself@test.com",
    "SMTP_PASSWD": "passwd"
}

@patch('smtplib.SMTP.send_message')
def send_message(self):
    return

patcher = patch('__main__.thing', first='one', send_message='two')

smtplib.SMTP = MagicMock()
smtplib.SMTP.login = MagicMock()


def test_mail(local_server_factory):
    local_server = local_server_factory(MailMicroService(env=env))
    response = local_server.make_call(requests.post, '/send', json={"subject": "Test mail",
                                                                    "from_addr": "myself@test.com",
                                                                    "to_addrs": ["you@test.com"]},
                                      timeout=300.5)
    assert response.status_code == 200
    assert response.text == "Mail sent to you@test.com"
    # smtplib.SMTP.login.assert_called_with("myself@test.com", "passwd")
    # send_message.assert_called()
