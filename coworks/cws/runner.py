import contextlib
import logging
import os
import socket
import sys
import threading
import urllib.parse
from threading import Thread, Event

import chalice.local
import click
from chalice.config import Config
from chalice.local import ChaliceRequestHandler, LocalGateway, LocalDevServer

from .command import CwsCommand
from ..utils import threaded


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

    @threaded
    def _execute(self, *, project_dir, workspace, host, port, debug, **options):
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
        os.environ['WORKSPACE'] = workspace
        ms.config.load_environment_variables(project_dir)
        if ms.entries is None:
            ms.deferred_init(workspace)

        if debug:
            logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')

        factory = CwsFactory(ms, project_dir, debug=debug)
        config = factory.mock_config_obj(ms)
        ms.local_server = LocalDevServer(ms, config, host, port, handler_cls=CwsRequestHandler)
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


class ThreadedLocalServer(Thread):
    threaded_servers = {}

    def __init__(self, *, port=None, host='localhost'):
        super().__init__()
        self._app_object = None
        self._config = None
        self._host = host
        self._port = port or self.unused_tcp_port()
        self._server = None
        self._server_ready = Event()

    def wait_for_server_ready(self):
        self._server_ready.wait()

    def configure(self, app_object, config=None, **kwargs):
        self._app_object = app_object
        self._config = config if config else Config()

    def run(self):
        self._server = LocalDevServer(self._app_object, self._config, self._host, self._port)
        self._server_ready.set()
        self._server.serve_forever()

    def make_call(self, method, path, timeout=0.5, **kwarg):
        self._server_ready.wait()
        return method('http://{host}:{port}{path}'.format(
            path=path, host=self._host, port=self._port), timeout=timeout, **kwarg)

    def shutdown(self):
        if self._server is not None:
            self._server.server.shutdown()

    @classmethod
    def unused_tcp_port(cls):
        with contextlib.closing(socket.socket()) as sock:
            sock.bind(('localhost', 0))
            return sock.getsockname()[1]
