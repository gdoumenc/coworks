import os
import smtplib
from email import message
from io import BytesIO
from unittest import mock

import pytest

from coworks import TechMicroService
from coworks.blueprint.mail_blueprint import Mail

smtp_mock = mock.MagicMock()
smtp_mock.return_value.__enter__.return_value.login = login_mock = mock.Mock()
smtp_mock.return_value.__enter__.return_value.send_message = send_mock = mock.Mock()

email_mock = mock.MagicMock()
email_mock.return_value.add_attachment = add_mock = mock.Mock()


class MailMS(TechMicroService):

    def __init__(self, **mail_names):
        super().__init__('mail')
        self.register_blueprint(Mail(**mail_names))
        self.any_token_authorized = True


class TestClass:

    def test_wrong_init(self):
        with pytest.raises(OSError) as pytest_wrapped_e:
            app = MailMS()
            with app.test_client() as c:
                response = c.post('/send')
        assert pytest_wrapped_e.type == OSError

    @mock.patch.dict(os.environ, {
        "SMTP_SERVER": "mail.test.com:587",
        "SMTP_LOGIN": "myself@test.com",
        "SMTP_PASSWD": "passwd"
    })
    def test_wrong_params(self):
        mail_names = {
            'env_server_var_name': 'SMTP_SERVER',
            'env_login_var_name': 'SMTP_LOGIN',
            'env_passwd_var_name': 'SMTP_PASSWD',
        }
        app = MailMS(**mail_names)
        with app.test_client() as c:
            data = {
                'subject': "Test",
            }
            response = c.post('/send', data=data)
            assert response.status_code == 400
            assert response.get_data(as_text=True) == "From address not defined (from_addr:str)"

    @mock.patch.dict(os.environ, {
        "SMTP_SERVER": "mail.test.com:587",
        "SMTP_LOGIN": "myself@test.com",
        "SMTP_PASSWD": "passwd"
    })
    def test_wrong_params(self, auth_headers):
        app = MailMS(env_var_prefix='SMTP')
        with app.test_client() as c:
            data = {
                'subject': "Test",
            }
            response = c.post('/send', data=data, headers=auth_headers)
            assert response.status_code == 400
            assert response.get_data(as_text=True) == "From address not defined (from_addr:str)"

    @mock.patch.dict(os.environ, {
        "SMTP_SERVER": "mail.test.com:587",
        "SMTP_LOGIN": "myself@test.com",
        "SMTP_PASSWD": "passwd"
    })
    @mock.patch.object(smtplib, 'SMTP', smtp_mock)
    def test_send_text(self, auth_headers):
        app = MailMS(env_var_prefix='SMTP')
        with app.test_client() as c:
            data = {
                'subject': "Test",
                'from_addr': "from@test.fr",
                'to_addrs': "to@test.fr",
            }
            response = c.post('/send', data=data, headers=auth_headers)
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "Mail sent to to@test.fr"
            login_mock.assert_called_with('myself@test.com', 'passwd')
            send_mock.assert_called_once()

    @mock.patch.dict(os.environ, {
        "SMTP_SERVER": "mail.test.com:587",
        "SMTP_LOGIN": "myself@test.com",
        "SMTP_PASSWD": "passwd"
    })
    @mock.patch.object(smtplib, 'SMTP', smtp_mock)
    @mock.patch.object(message, 'EmailMessage', email_mock)
    def test_send_attachment(self, auth_headers):
        app = MailMS(env_var_prefix='SMTP')
        with app.test_client() as c:
            file = BytesIO(b"hello {{ world_name }}")
            data = {
                'subject': "Test",
                'from_addr': "from@test.fr",
                'to_addrs': "to@test.fr",
                'attachments': [(file, 'file.txt')]
            }
            response = c.post('/send', data=data, headers=auth_headers)
            assert response.status_code == 200
            login_mock.assert_called_with('myself@test.com', 'passwd')
            add_mock.assert_called_once()
