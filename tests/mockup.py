import smtplib
from email import message
from unittest.mock import Mock, MagicMock

#
# Email
#

email_mock = message.EmailMessage()
email_mock.set_content = Mock()
email_mock.add_attachment = Mock()


class EmailMessageMock:
    def __new__(cls, *args, **kwargs):
        return email_mock


message.EmailMessage = EmailMessageMock

smtp_mock = MagicMock()
smtp_mock.__enter__.return_value = smtp_mock
smtp_mock.send_message.return_value = "Mail sent to you@test.com"


class SMTPMock:
    def __new__(cls, *args, **kwargs):
        return smtp_mock


smtplib.SMTP = SMTPMock
