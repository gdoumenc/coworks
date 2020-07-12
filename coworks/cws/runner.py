import logging
import os
import sys
import threading
import urllib.parse

import chalice.local
import click
from chalice.local import LocalDevServer, ChaliceRequestHandler, LocalGateway

from .command import CwsCommand


class CwsRunner(CwsCommand):
    def __init__(self, app=None, name='run'):
        super().__init__(app, name=name)

    @property
    def options(self):
        return [
            *super().options,
            click.option('-h', '--host', default='127.0.0.1'),
            click.option('-p', '--port', default=8000, type=click.INT),
            click.option('--debug/--no-debug', default=False, help='Print debug logs to stderr.')
        ]

    def _execute(self, options):
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
        os.environ['WORKSPACE'] = options.workspace
        ms.config.load_environment_variables(options.project_dir)
        if ms.entries is None:
            ms.deferred_init(options.workspace)

        if options['debug']:
            logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')

        factory = CwsFactory(ms, options.project_dir, debug=options['debug'])
        config = factory.mock_config_obj(ms)
        ms.local_server = LocalDevServer(ms, config, options['host'], options['port'],
                                         handler_cls=CwsRequestHandler)
        ms.__class__ = type('LocalMicroService', (ms.__class__, ThreadedMixin), {})
        ms.local_server.serve_forever()


class CwsRequestHandler(ChaliceRequestHandler):
    """Request handler redefined to quote query parameters."""

    def __init__(self, request, client_address, server, app_object, config):
        chalice.local.LocalGateway = CwsLocalGateway
        super().__init__(request, client_address, server, app_object, config)
        chalice.local.LocalGateway = LocalGateway

    def parse_request(self):
        request = super().parse_request()
        self.path = urllib.parse.quote(self.path)
        return request


class CwsLocalGateway(LocalGateway):
    """Local gateway redefined to unquote query parameters."""

    def _generate_lambda_event(self, method, path, headers, body):
        path = urllib.parse.unquote(path)
        return super()._generate_lambda_event(method, path, headers, body)


class ThreadedMixin:
    _THREAD_LOCAL = threading.local()

    @property
    def current_request(self):
        return self._THREAD_LOCAL.current_request

    @current_request.setter
    def current_request(self, value):
        self._THREAD_LOCAL.current_request = value
