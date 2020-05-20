from unittest.mock import MagicMock
import pytest
import requests
import os

from coworks.tech import MailMicroService

env = {
    "SMTP_SERVER": "mail.test.com:587",
    "SMTP_LOGIN": "myself@test.com",
    "SMTP_PASSWD": "passwd"
}


@pytest.mark.local
class ATestMail:
    def test_send(self, local_server_factory, smtp_mock_fixture, email_mock_fixture):
        local_server = local_server_factory(MailMicroService(env=env))

        text_attachment = open("attachment.txt", "w+")
        text_attachment.write("This is the content of the attachemnt")
        text_attachment.close()
        text_attachment = open("attachment.txt", "r")

        response = local_server.make_call(requests.post, '/send',
                                          data={'subject': "Test mail",
                                                'from_addr': "myself@test.com",
                                                'to_addrs': ["you@test.com", "and@test.com"],
                                                'body': "content"},
                                          files={
                                              'attachments': ('attachment.txt', text_attachment, 'text/plain'),
                                          })
        text_attachment.close()
        os.remove("attachment.txt")
        assert response.status_code == 200
        smtp_mock_fixture.login.assert_called_once_with("myself@test.com", "passwd")
        email_mock_fixture.set_content.assert_called_once_with('content')
        email_mock_fixture.add_attachment.assert_called_with(b'This is the content of the attachemnt',
                                                             filename='attachment.txt', maintype='text', subtype='plain')
        assert email_mock_fixture["Subject"] == "Test mail"
        assert email_mock_fixture["From"] == "myself@test.com"
        assert email_mock_fixture["To"] == "you@test.com, and@test.com"
        assert response.text == "Mail sent to you@test.com, and@test.com"
        smtp_mock_fixture.send_message.assert_called()
