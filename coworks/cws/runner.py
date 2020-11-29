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
from aws_xray_sdk.core import xray_recorder
from chalice.cli import run_local_server, reloader
from chalice.config import Config
from chalice.local import ChaliceRequestHandler, LocalGateway, LocalDevServer

from .command import CwsCommand


class CwsRunner(CwsCommand):
    def __init__(self, app=None, name='run'):
        super().__init__(app, name=name)
        xray_recorder.configure(context_missing="LOG_ERROR")

    @property
    def options(self):
        return [
            click.option('-h', '--host', default='127.0.0.1'),
            click.option('-p', '--port', default=8000, type=click.INT),
            click.option('--autoreload', is_flag=True, help='Reload server on source changes.'),
            click.option('--debug', is_flag=True, help='Print debug logs to stderr.')
        ]

    def _execute(self, *, project_dir, workspace, host, port, autoreload, debug, **options):
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

        if autoreload:
            class _ThreadedLocalServer(ThreadedLocalServer):

                def __init__(self, *args):
                    super().__init__(*args)
                    self._app_object = self
                    self._config = Config()
                    self._host = host
                    self._port = port
                    self._server = LocalDevServer(ms, self._config, self._host, self._port)

            rc = reloader.run_with_reloader(_ThreadedLocalServer, os.environ, project_dir)
            sys.exit(rc)
        else:
            factory = CwsFactory(ms, project_dir, debug=debug)
            run_local_server(factory, host, port, workspace)


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
    def __init__(self, *, port=None, host='localhost'):
        super().__init__()
        self._app_object = None
        self._config = None
        self._host = host
        self._port = port or self.unused_tcp_port()
        self._server = None
        self._server_ready = Event()

    def configure(self, app_object, config=None, **kwargs):
        self._app_object = app_object
        self._config = config if config else Config()

    def run(self):
        self._server = LocalDevServer(self._app_object, self._config, self._host, self._port, )
        # handler_cls=CwsRequestHandler)
        self._server_ready.set()
        self._server.serve_forever()

    def serve_forever(self):
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


def run_with_reloader(app, **kwargs):
    kwargs.setdefault('autoreload', True)
    sys.argv = [sys.executable, sys.argv[0]]
    app.execute('run', **kwargs)
