import sentry_sdk
import typing as t

if t.TYPE_CHECKING:
    from coworks import TechMicroService

MIDDLEWARE_NAME = 'sentry'


class SentryMiddleware:

    def __init__(self, app: "TechMicroService", sentry_entry: str, name=MIDDLEWARE_NAME, **kwargs):
        self._app = app
        sentry_sdk.init(sentry_entry, **kwargs)
        app.logger.debug(f"Initializing sentry middleware {name}")
