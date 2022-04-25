import os
import typing as t

import sentry_sdk
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

from ..utils import get_app_workspace

if t.TYPE_CHECKING:
    from coworks import TechMicroService

MIDDLEWARE_NAME = 'sentry'


class SentryMiddleware:

    def __init__(self, app: "TechMicroService", env_dsn_name: str = 'SENTRY_DSN', name=MIDDLEWARE_NAME):
        def first():
            if get_app_workspace() != 'local':
                app.logger.debug(f"Initializing sentry middleware {name}")
                sentry_sdk.init(
                    dsn=os.getenv(env_dsn_name),
                    integrations=[AwsLambdaIntegration()],
                )

        app.before_first_request_funcs = [first, *app.before_first_request_funcs]
