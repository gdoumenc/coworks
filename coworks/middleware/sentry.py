import os
import sentry_sdk
import typing as t
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

if t.TYPE_CHECKING:
    from coworks import TechMicroService

MIDDLEWARE_NAME = 'sentry'


class SentryMiddleware:

    def __init__(self, app: "TechMicroService", env_dsn_name: str = 'SENTRY_DSN', name=MIDDLEWARE_NAME):
        def first():
            if os.getenv('WORKSPACE') != 'local':
                app.logger.debug(f"Initializing sentry middleware {name}")
                sentry_sdk.init(
                    dsn=os.getenv(env_dsn_name),
                    integrations=[AwsLambdaIntegration()],
                )

        app.before_first_request_funcs = [first, *app.before_first_request_funcs]
