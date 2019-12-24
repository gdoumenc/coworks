import os
from email.message import EmailMessage
import smtplib

from chalice import ChaliceViewError

from ..coworks import TechMicroService


class MailMicroService(TechMicroService):
    """ POST http://microservice/send
        Content-Type: application/json

        {
          "starttls": true,
          "from_addr": "myself@domain.com",
          "to_addrs": ["myself@domain.com"],
          "subject" : "test",
          "body": "test"
        }"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.smtp_server = self.smtp_login = self.smtp_passwd = None

    def check_env_vars(self):
        self.smtp_server = os.getenv('SMTP_SERVER')
        if not self.smtp_server:
            raise EnvironmentError('SMTP_SERVER not defined in environment')
        self.smtp_login = os.getenv('SMTP_LOGIN')
        if not self.smtp_login:
            raise EnvironmentError('SMTP_LOGIN not defined in environment')
        self.smtp_passwd = os.getenv('SMTP_PASSWD')
        if not self.smtp_passwd:
            raise EnvironmentError('SMTP_PASSWD not defined in environment')

    def post_send(self, subject="", from_addr=None, to_addrs=None, body="", starttls=False):
        self.check_env_vars()
        from_addr = from_addr or os.getenv('from_addr')
        if not from_addr:
            raise ChaliceViewError("From address not defined")
        to_addrs = to_addrs or os.getenv('to_addrs')
        if not to_addrs:
            raise ChaliceViewError("To addresses not defined")
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = from_addr
        msg['To'] = ', '.join(to_addrs)
        msg.set_content(body)
        try:
            with smtplib.SMTP(self.smtp_server) as server:
                if starttls:
                    server.starttls()
                server.login(self.smtp_login, self.smtp_passwd)
                server.send_message(msg)
            return f"Mail sent to {msg['To']}"
        except smtplib.SMTPAuthenticationError:
            raise ChaliceViewError("Wrong username/password.")
