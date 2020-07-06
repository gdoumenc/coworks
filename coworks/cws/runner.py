import logging
import sys
import threading

import click
from chalice.local import LocalDevServer

from .command import CwsCommand
from .. import TechMicroService


class CwsRunner(CwsCommand):
    def __init__(self, app=None, name='run'):
        super().__init__(app, name=name)

    @property
    def options(self):
        return (
            click.option('-h', '--host', default='127.0.0.1'),
            click.option('-p', '--port', default=8000, type=click.INT),
            click.option('--debug/--no-debug', default=False, help='Print debug logs to stderr.')
        )

    def _execute(self, host: str = '127.0.0.1', port: int = 8000, debug=True, *, workspace, **kwargs):
        """ Runs the microservice in a local Chalice emulator.

        :param host: the hostname to listen on.
        :param port: the port of the webserver.
        :param project_dir: to be able to import the microservice module.
        :param debug: if given, enable or disable debug mode.
        :param workspace: the workspace stagging run mode.
        :return: None
        """

        # chalice.cli package is not defined in deployment
        from .factory import CwsFactory

        ms = self.app
        project_dir = kwargs['project_dir']
        ms.config.load_environment_variables(project_dir)
        if ms.entries is None:
            ms.deferred_init(workspace=workspace)

        if debug:
            logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')

        factory = CwsFactory(ms, project_dir, debug=debug)
        config = factory.mock_config_obj(ms)
        ms.local_server = LocalDevServer(ms, config, host, port)
        ms.__class__ = LocalMicroService
        ms.local_server.serve_forever()


class LocalMicroService(TechMicroService):
    _THREAD_LOCAL = threading.local()

    @property
    def current_request(self):
        return self._THREAD_LOCAL.current_request

    @current_request.setter
    def current_request(self, value):
        self._THREAD_LOCAL.current_request = value
