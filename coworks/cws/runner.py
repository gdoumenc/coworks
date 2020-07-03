import logging
import sys

import click

from .command import CwsCommand


class CwsRunner(CwsCommand):
    def __init__(self, app=None):
        super().__init__(app, name='run')

    @property
    def options(self):
        return (
            click.option('-h', '--host', default='127.0.0.1'),
            click.option('-p', '--port', default=8000, type=click.INT),
            click.option('--debug/--no-debug', default=False, help='Print debug logs to stderr.')
        )

    def _execute(self, host: str = '127.0.0.1', port: int = 8000, debug=True, **kwargs):
        """ Runs the microservice in a local Lambda emulator.

        :param host: the hostname to listen on.
        :param port: the port of the webserver.
        :param project_dir: to be able to import the microservice module.
        :param debug: if given, enable or disable debug mode.
        :return: None
        """

        # chalice.cli package is not defined in deployment
        from .factory import CwsFactory

        project_dir = kwargs['project_dir']
        self.app.config.load_environment_variables(project_dir)

        if debug:
            logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')

        factory = CwsFactory(self.app, project_dir, debug=debug)
        config = factory.mock_config_obj(self.app)
        factory.run_local_server(self.app, config, host, port)
