class Middleware:

    def __init__(self, app):
        self._app = app

    def deferred_init(self, workspace):
        self._app.deferred_init(workspace)
