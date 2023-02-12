import os
import smtplib
import typing as t
from email import message
from email.utils import formataddr
from email.utils import formatdate
from email.utils import make_msgid

import requests
from flask import current_app
from flask import render_template_string
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest
from werkzeug.exceptions import InternalServerError

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
    - env_port_var_name: Variable name for the SMPT port.
    - env_login_var_name: Variable name for the login.
    - env_passwd_var_name: Variable name for the password.
    """

    def __init__(self, name: str = "mail",
                 env_server_var_name: str = '', env_port_var_name: str = '',
                 env_login_var_name: str = '', env_passwd_var_name: str = '',
                 env_var_prefix: str = '', **kwargs):
        super().__init__(name=name, **kwargs)
        if env_var_prefix:
            env_server_var_name = f"{env_var_prefix}_SERVER"
            env_port_var_name = f"{env_var_prefix}_PORT"
            env_login_var_name = f"{env_var_prefix}_LOGIN"
            env_passwd_var_name = f"{env_var_prefix}_PASSWD"

        self.smtp_server = os.getenv(env_server_var_name)
        if not self.smtp_server:
            raise RuntimeError(f'{env_server_var_name} not defined in environment.')
        self.smtp_port = int(os.getenv(env_port_var_name, 587))
        self.smtp_login = os.getenv(env_login_var_name)
        if not self.smtp_login:
            raise RuntimeError(f'{env_login_var_name} not defined in environment.')
        self.smtp_passwd = os.getenv(env_passwd_var_name)
        if not self.smtp_passwd:
            raise RuntimeError(f'{env_passwd_var_name} not defined in environment.')

    @entry
    def post_send(self, subject: str = "", from_addr: str = None, from_name: str = '', reply_to: str = None,
                  to_addrs: [str] = None, cc_addrs: [str] = None, bcc_addrs: [str] = None,
                  body: str = "", body_template: str = None, body_type="plain",
                  attachments: t.Union[FileStorage, t.Iterator[FileStorage]] = None, attachment_urls: dict = None,
                  starttls=True, data: dict = None):
        """ Send mail.
        To send attachments, add files in the body of the request as multipart/form-data.

        :param subject: Email's subject (required).
        :param from_addr: From recipient.
        :param from_name: Name besides from_address.
        :param reply_to: Reply recipient.
        :param to_addrs: Email's recipients. Accept one or several email addresses separated by commas.
        :param cc_addrs: Email's cc recipients. Accept one or several email addresses separated by commas.
        :param bcc_addrs: Email's bcc recipients. Accept one or several email addresses separated by commas.
        :param body: Email's body (required if body_template not defined).
        :param body_template: Email's body template (required if body not defined).
        :param body_type: Email's body type.
        :param attachments: File storage.
        :param attachment_urls: File url.
        :param starttls: Puts the connection to the SMTP server into TLS mode.
        :param data: Jinnja context for the templating.
        """

        from_addr = from_addr or os.getenv('from_addr')
        if not from_addr:
            raise BadRequest("From address not defined (from_addr:str)")
        to_addrs = to_addrs or os.getenv('to_addrs')
        if not to_addrs:
            raise BadRequest("To addresses not defined (to_addrs:[str])")

        if body_template is not None:
            if body is not None:
                raise BadRequest("Body and body_template parameters both defined.")
            body = render_template_string(body_template, **data)

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
                current_app.logger.info("Attachments defined")
                if not isinstance(attachments, list):
                    attachments = [attachments]
                for attachment in attachments:
                    msg.add_attachment(attachment.stream.read(), maintype='multipart', subtype=attachment.content_type)
                    current_app.logger.info(f"Add attachment {attachment}")

            if attachment_urls:
                current_app.logger.info("Attachments urls defined")
                for attachment_name, attachment_url in attachment_urls.items():
                    response = requests.get(attachment_url)
                    if response.status_code == 200:
                        attachment = response.content
                        maintype, subtype = response.headers['Content-Type'].split('/')
                        msg.add_attachment(attachment, maintype=maintype, subtype=subtype,
                                           filename=attachment_name)
                        current_app.logger.info(f"Add attachment {attachment_name} - size {len(attachment)}")
                    else:
                        return f"Failed to download attachment, error {response.status_code}.", 400

        except Exception as e:
            raise BadRequest(f"Cannot create email message (Error: {str(e)}).")

        # Send email
        try:
            with smtplib.SMTP(self.smtp_server, port=self.smtp_port) as server:
                if starttls:
                    server.starttls()
                server.login(self.smtp_login, self.smtp_passwd)
                server.send_message(msg)

            resp = f"Mail sent to {msg['To']}"
            current_app.logger.info(resp)
            return resp
        except smtplib.SMTPAuthenticationError:
            raise ConnectionError("Wrong username/password : cannot connect.")
        except Exception as e:
            raise InternalServerError(f"Cannot send email message (Error: {str(e)}).")
