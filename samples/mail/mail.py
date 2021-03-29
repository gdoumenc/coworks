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
            app.log.info(event)

    @staticmethod
    def auth(auth_request):
        return auth_request.token == os.getenv('TOKEN')

    @entry
    def get(self):
        return app.blueprints['mail'].post_send(subject='test get entry', body='Manual test',
                                                from_addr='gdoumenc@fpr-coworks.com',
                                                to_addrs='gdoumenc@fpr-coworks.com')


app = MailMicroService(name="sample-mail-microservice", debug=True, configs=[LocalConfig(), DevConfig()])
app.register_blueprint(Admin(), url_prefix='admin')
app.register_blueprint(Mail('SMTP_SERVER', 'SMTP_LOGIN', 'SMTP_PASSWD'))
XRayContextManager(app, xray_recorder)


@app.schedule('rate(1 hour)', name='hourly', description="Mail sent every hour for testing.")
@app.schedule('cron(00 15 * * ? *)', name="daily", description="Mail sent at 3pm for testing.")
def every_sample(name):
    """This doc string will serve as schedule event description if not defined."""
    app.blueprints['mail'].post_send(subject='test event bridge', body=f"Made by {name}",
                                     from_addr='gdoumenc@fpr-coworks.com',
                                     to_addrs='gdoumenc@fpr-coworks.com')


if __name__ == '__main__':
    app.execute("run", project_dir='.', module='mail', workspace='dev')
