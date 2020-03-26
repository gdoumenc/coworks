import cgi
import os
import smtplib
from email.message import EmailMessage
from typing import List

from aws_xray_sdk.core import xray_recorder
from chalice import ChaliceViewError, BadRequestError
from requests_toolbelt.multipart import decoder

from ..coworks import TechMicroService


class MailMicroService(TechMicroService):
    """Mail microservice"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.smtp_server = self.smtp_login = self.smtp_passwd = None

        @self.before_first_request
        def check_env_vars():
            self.smtp_server = os.getenv('SMTP_SERVER')
            if not self.smtp_server:
                raise EnvironmentError('SMTP_SERVER not defined in environment')
            self.smtp_login = os.getenv('SMTP_LOGIN')
            if not self.smtp_login:
                raise EnvironmentError('SMTP_LOGIN not defined in environment')
            self.smtp_passwd = os.getenv('SMTP_PASSWD')
            if not self.smtp_passwd:
                raise EnvironmentError('SMTP_PASSWD not defined in environment')

    def _add_attachments(self, msg, content_type):
        multipart_decoder = decoder.MultipartDecoder(self.current_request.raw_body, content_type)
        for part in multipart_decoder.parts:
            headers = {k.decode('utf-8'): v.decode('utf-8') for k, v in part.headers.items()}
            _, content_disposition_params = cgi.parse_header(headers['Content-Disposition'])
            maintype, subtype = headers['Content-Type'].split("/")
            msg.add_attachment(part.content, maintype=maintype, subtype=subtype,
                               filename=content_disposition_params['filename'])

    def post_send(self, subject="", from_addr: str = None, to_addrs: List[str] = None, body="", starttls=False):
        """ Send mail.
        To send attachments, add files in the body of the request as multipart/form-data. """

        from_addr = from_addr or os.getenv('from_addr')
        if not from_addr:
            raise BadRequestError("From address not defined (from_addr:str)")
        to_addrs = to_addrs or os.getenv('to_addrs')
        if not to_addrs:
            raise BadRequestError("To addresses not defined (to_addrs:[str])")
        content_type = self.current_request.headers.get('content-type')

        # Creates email
        try:
            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = from_addr
            msg['To'] = to_addrs if isinstance(to_addrs, str) else ', '.join(to_addrs)
            msg.set_content(body)
            if content_type and content_type.startswith('multipart/form-data'):
                self._add_attachments(msg, content_type)
        except Exception as e:
            raise ChaliceViewError(f"Cannot create email message (Error: {str(e)}).")

        # Send emails
        try:
            with smtplib.SMTP(self.smtp_server) as server:
                if starttls:
                    server.starttls()
                server.login(self.smtp_login, self.smtp_passwd)
                subsegment = xray_recorder.begin_subsegment(f"SMTP sending")
                try:
                    if subsegment:
                        subsegment.put_metadata('message', msg.as_string())
                    server.send_message(msg)
                finally:
                    xray_recorder.end_subsegment()

            return f"Mail sent to {msg['To']}"
        except smtplib.SMTPAuthenticationError:
            raise BadRequestError("Wrong username/password.")
        except Exception as e:
            raise ChaliceViewError(f"Cannot send email message (Error: {str(e)}).")
