import smtplib
from unittest.mock import MagicMock

import pytest
import requests

from coworks.tech import MailMicroService

env = {
    "SMTP_SERVER": "mail.test.com:587",
    "SMTP_LOGIN": "myself@test.com",
    "SMTP_PASSWD": "passwd"
}

mock = MagicMock()
mock.__enter__ = MagicMock(return_value=mock)


class SMTPMock:
    def __new__(cls, *args, **kwargs):
        return mock


smtplib.SMTP = SMTPMock


@pytest.mark.tech
class TestMail:

    def test_send(self, local_server_factory):
        local_server = local_server_factory(MailMicroService(env=env))
        response = local_server.make_call(requests.post, '/send', json={"subject": "Test mail",
                                                                        "from_addr": "myself@test.com",
                                                                        "to_addrs": ["you@test.com"]})
        assert response.status_code == 200
        assert response.text == "Mail sent to you@test.com"
        mock.login.assert_called_with("myself@test.com", "passwd")
        mock.send_message.assert_called()
