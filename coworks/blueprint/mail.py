import os
import smtplib
from email.message import EmailMessage

import requests
from chalice import ChaliceViewError, BadRequestError

from coworks import Blueprint, FileParam


class Mail(Blueprint):
    """Mail blueprint."""

    def __init__(self, env_server_var_name, env_login_var_name, env_passwd_var_name, **kwargs):
        super().__init__(**kwargs)
        self.env_server_var_name = env_server_var_name
        self.env_login_var_name = env_login_var_name
        self.env_passwd_var_name = env_passwd_var_name
        self.smtp_server = self.smtp_login = self.smtp_passwd = None

        @self.before_first_activation
        def check_env_vars(event, context):
            self.smtp_server = os.getenv(self.env_server_var_name)
            if not self.smtp_server:
                raise EnvironmentError(f'{self.env_server_var_name} not defined in environment.')
            self.smtp_login = os.getenv(self.env_login_var_name)
            if not self.smtp_login:
                raise EnvironmentError(f'{self.env_login_var_name} not defined in environment.')
            self.smtp_passwd = os.getenv(env_passwd_var_name)
            if not self.smtp_passwd:
                raise EnvironmentError(f'{env_passwd_var_name} not defined in environment.')

    def post_send(self, subject="", from_addr: str = None, to_addrs: [str] = None, cc_addrs: [str] = None,
                  bcc_addrs: [str] = None, body="",
                  attachments: [FileParam] = None, attachment_urls: dict = None, subtype="plain", starttls=True):
        """ Send mail.
        To send attachments, add files in the body of the request as multipart/form-data. """

        from_addr = from_addr or os.getenv('from_addr')
        if not from_addr:
            raise BadRequestError("From address not defined (from_addr:str)")
        to_addrs = to_addrs or os.getenv('to_addrs')
        if not to_addrs:
            raise BadRequestError("To addresses not defined (to_addrs:[str])")

        # Creates email
        try:
            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = from_addr
            msg['To'] = to_addrs if isinstance(to_addrs, str) else ', '.join(to_addrs)
            if cc_addrs:
                msg['Cc'] = cc_addrs if isinstance(cc_addrs, str) else ', '.join(cc_addrs)
            if bcc_addrs:
                msg['Bcc'] = bcc_addrs if isinstance(bcc_addrs, str) else ', '.join(bcc_addrs)
            msg.set_content(body, subtype=subtype)

            if attachments:
                if not isinstance(attachments, list):
                    attachments = [attachments]
                for attachment in attachments:
                    if not attachment.mime_type:
                        raise BadRequestError(f"Mime type of the attachment {attachment.file.name} is not defined.")
                    maintype, subtype = attachment.mime_type.split("/")
                    msg.add_attachment(attachment.file.read(), maintype=maintype, subtype=subtype,
                                       filename=attachment.file.name)

            if attachment_urls:
                for attachment_name, attachment_url in attachment_urls.items():
                    response = requests.get(attachment_url)
                    if response.status_code == 200:
                        attachment = response.content
                        maintype, subtype = response.headers['Content-Type'].split('/')
                        msg.add_attachment(attachment, maintype=maintype, subtype=subtype,
                                           filename=attachment_name)
                    else:
                        raise BadRequestError(f"Failed to download attachment, error {response.status_code}.")

        except Exception as e:
            raise ChaliceViewError(f"Cannot create email message (Error: {str(e)}).")

        # Send emails
        try:
            with smtplib.SMTP(self.smtp_server) as server:
                if starttls:
                    server.starttls()
                server.login(self.smtp_login, self.smtp_passwd)
                server.send_message(msg)

            return f"Mail sent to {msg['To']}"
        except smtplib.SMTPAuthenticationError:
            raise BadRequestError("Wrong username/password.")
        except Exception as e:
            raise ChaliceViewError(f"Cannot send email message (Error: {str(e)}).")
