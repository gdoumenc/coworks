import os
import smtplib
import typing as t
from email import message
from email.utils import formataddr
from email.utils import formatdate
from email.utils import make_msgid

import requests
from flask import current_app
from werkzeug.datastructures import FileStorage

from coworks import Blueprint
from coworks import entry


#
# BLUEPRINT PART
#

class Mail(Blueprint):
    """Mail blueprint.
    Initialization parameters must be in environment (Twelve-Factor App).
    Environment variables needed:
    - env_server_var_name: Variable name for the SMTP server.
    - env_login_var_name: Variable name for the login.
    - env_passwd_var_name: Variable name for the password.
    """

    def __init__(self, name: str = "mail",
                 env_server_var_name: str = '', env_port_var_name: str = '',
                 env_login_var_name: str = '', env_passwd_var_name: str = '',
                 env_var_prefix: str = '', **kwargs):
        super().__init__(name=name, **kwargs)
        self.smtp_server = self.smtp_port = self.smtp_login = self.smtp_passwd = None
        if env_var_prefix:
            self.env_server_var_name = f"{env_var_prefix}_SERVER"
            self.env_port_var_name = f"{env_var_prefix}_PORT"
            self.env_login_var_name = f"{env_var_prefix}_LOGIN"
            self.env_passwd_var_name = f"{env_var_prefix}_PASSWD"
        else:
            self.env_server_var_name = env_server_var_name
            self.env_port_var_name = env_port_var_name
            self.env_login_var_name = env_login_var_name
            self.env_passwd_var_name = env_passwd_var_name

    def init_app(self, app):
        self.smtp_server = os.getenv(self.env_server_var_name)
        if not self.smtp_server:
            raise EnvironmentError(f'{self.env_server_var_name} not defined in environment.')
        self.smtp_port = int(os.getenv(self.env_port_var_name, 587))
        self.smtp_login = os.getenv(self.env_login_var_name)
        if not self.smtp_login:
            raise EnvironmentError(f'{self.env_login_var_name} not defined in environment.')
        self.smtp_passwd = os.getenv(self.env_passwd_var_name)
        if not self.smtp_passwd:
            raise EnvironmentError(f'{self.env_passwd_var_name} not defined in environment.')

    @entry
    def post_send(self, subject="", from_addr: str = None, from_name: str = '', reply_to: str = None,
                  to_addrs: [str] = None, cc_addrs: [str] = None, bcc_addrs: [str] = None,
                  body="", body_type="plain",
                  attachments: t.Union[FileStorage, t.List[FileStorage]] = None, attachment_urls: dict = None,
                  starttls=True):
        """ Send mail.
        To send attachments, add files in the body of the request as multipart/form-data.
        """

        from_addr = from_addr or os.getenv('from_addr')
        if not from_addr:
            return "From address not defined (from_addr:str)", 400
        to_addrs = to_addrs or os.getenv('to_addrs')
        if not to_addrs:
            return "To addresses not defined (to_addrs:[str])", 400

        # Creates email
        try:
            from_ = formataddr((from_name if from_name else False, from_addr))
            msg = message.EmailMessage()
            msg["Date"] = formatdate(localtime=True)
            msg["Message-ID"] = make_msgid()
            msg['Subject'] = subject
            msg['From'] = from_
            if reply_to is not None:
                msg['Reply-To'] = reply_to
            msg['To'] = to_addrs if isinstance(to_addrs, str) else ', '.join(to_addrs)
            if cc_addrs:
                msg['Cc'] = cc_addrs if isinstance(cc_addrs, str) else ', '.join(cc_addrs)
            if bcc_addrs:
                msg['Bcc'] = bcc_addrs if isinstance(bcc_addrs, str) else ', '.join(bcc_addrs)
            msg.set_content(body, subtype=body_type)

            if attachments:
                if not isinstance(attachments, list):
                    attachments = [attachments]
                for attachment in attachments:
                    msg.add_attachment(attachment.stream.read(), maintype='multipart', subtype=attachment.content_type)

            if attachment_urls:
                for attachment_name, attachment_url in attachment_urls.items():
                    response = requests.get(attachment_url)
                    if response.status_code == 200:
                        attachment = response.content
                        maintype, subtype = response.headers['Content-Type'].split('/')
                        msg.add_attachment(attachment, maintype=maintype, subtype=subtype,
                                           filename=attachment_name)
                        current_app.logger.debug(f"Add attachment {attachment_name} - size {len(attachment)}")
                    else:
                        return f"Failed to download attachment, error {response.status_code}.", 400

        except Exception as e:
            return f"Cannot create email message (Error: {str(e)}).", 400

        # Send email
        try:
            with smtplib.SMTP(self.smtp_server, port=self.smtp_port) as server:
                if starttls:
                    server.starttls()
                server.login(self.smtp_login, self.smtp_passwd)
                server.send_message(msg)

            resp = f"Mail sent to {msg['To']}"
            current_app.logger.debug(resp)
            return resp
        except smtplib.SMTPAuthenticationError:
            return "Wrong username/password : cannot connect.", 400
        except Exception as e:
            return f"Cannot send email message (Error: {str(e)}).", 400
