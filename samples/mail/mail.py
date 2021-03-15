import os

from aws_xray_sdk.core import xray_recorder

from config import LocalConfig, DevConfig
from coworks import TechMicroService, entry
from coworks.blueprint import Admin
from coworks.blueprint.mail import Mail
from coworks.context_manager import XRayContextManager


class MailMicroService(TechMicroService):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        @self.before_activation
        def check_env_vars(event, context):
            print(event)

    def auth(self, auth_request):
        valid = (auth_request.token == os.getenv('TOKEN'))
        return valid

    @entry
    def get(self):
        return self.entry('/send').call_post(subject='test', body='test', from_addr='gdoumenc@fpr-coworks.com',
                                             to_addrs='gdoumenc@fpr-coworks.com')


app = MailMicroService(name="sample-mail-microservice", configs=[LocalConfig(), DevConfig()])
app.register_blueprint(Admin(), url_prefix='admin')
app.register_blueprint(Mail('SMTP_SERVER', 'SMTP_LOGIN', 'SMTP_PASSWD'))
XRayContextManager(app, xray_recorder)

if __name__ == '__main__':
    app.execute("run", project_dir='.', module='website', workspace='local')
