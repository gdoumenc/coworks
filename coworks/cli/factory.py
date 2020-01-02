import os

from chalice.cli import CLIFactory


class CWSFactory(CLIFactory):
    def __init__(self, app, project_dir, debug, profile, environ=None):
        self.app = app
        super().__init__(project_dir, debug=debug, profile=profile, environ=environ)

    def load_chalice_app(self, environment_variables=None, **kwargs):
        if environment_variables is not None:
            self._environ.update(environment_variables)
            for key, val in self._environ.items():
                os.environ[key] = val
        return self.app

    def run_local_server(self, config, host, port):
        app_obj = config.chalice_app
        server = super().create_local_server(app_obj, config, host, port)
        server.serve_forever()
