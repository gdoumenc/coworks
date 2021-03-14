import contextlib
import logging
import os
import socket
import sys
from threading import Thread, Event

import click
from aws_xray_sdk.core import xray_recorder
from chalice.cli import run_local_server, reloader
from chalice.config import Config
from chalice.local import LocalDevServer

from .command import CwsCommand


class CwsRunner(CwsCommand):
    @property
    def options(self):
        return [
            *super().options,
            click.option('-h', '--host', default='127.0.0.1'),
            click.option('-p', '--port', default=8000, type=click.INT),
            click.option('--autoreload', is_flag=True, help='Reload server on source changes.'),
            click.option('--debug', is_flag=True, help='Print debug logs to stderr.')
        ]

    @classmethod
    def multi_execute(cls, project_dir, workspace, execution_list):
        """ Runs the microservice in a local Chalice emulator.
        """

        # chalice.cli package is not defined in deployment
        from .factory import CwsFactory

        for command, options in execution_list:
            os.environ['WORKSPACE'] = workspace
            command.app.config.load_environment_variables(project_dir)
            if command.app.entries is None:
                command.app.deferred_init(workspace)

            debug = options['debug']
            autoreload = options['autoreload']
            if debug:
                logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')

            if autoreload:
                if not options['_from_cws']:
                    sys.argv = [sys.executable, sys.argv[0]]

                class _ThreadedLocalServer(ThreadedLocalServer):

                    def __init__(self):
                        super().__init__()
                        self._app_object = self
                        self._config = Config()
                        self._host = options['host']
                        self._port = options['port']
                        self._server = LocalDevServer(command.app, self._config, self._host, self._port)

                rc = reloader.run_with_reloader(_ThreadedLocalServer, os.environ, project_dir)
                sys.exit(rc)
            else:
                factory = CwsFactory(command.app, project_dir, debug=debug)
                run_local_server(factory, options['host'], options['port'], workspace)

    def __init__(self, app=None, name='run'):
        super().__init__(app, name=name)
        xray_recorder.configure(context_missing="LOG_ERROR")


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
        self._server_ready.set()
        self._server.serve_forever()

    def serve_forever(self):
        self._server.serve_forever()

    def shutdown(self):
        if self._server is not None:
            self._server.server.shutdown()

    def make_call(self, method, path, timeout=0.5, **kwarg):
        self._server_ready.wait()
        return method(f'http://{self._host}:{self._port}{path}', timeout=timeout, **kwarg)

    @classmethod
    def unused_tcp_port(cls):
        with contextlib.closing(socket.socket()) as sock:
            sock.bind(('localhost', 0))
            return sock.getsockname()[1]
