import io

from werkzeug.middleware.profiler import ProfilerMiddleware

from coworks import Blueprint
from coworks import entry


class Profiler(Blueprint):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.output = io.StringIO()

    def init_app(self, app):
        app.wsgi_app = ProfilerMiddleware(app.wsgi_app, stream=self.output)

    @entry
    def get(self):
        profile = self.output.getvalue()
        self.output.seek(0)
        return profile
