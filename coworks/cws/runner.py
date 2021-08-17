import contextlib
import logging
import os
import socket
from threading import Thread, Event

import click
import sys
from aws_xray_sdk.core import xray_recorder
import click
from flask.cli import with_appcontext
from .command import CwsCommand


class CwsRunner():
    @property
    def options(self):
        return [
            *super().options,
            click.option('-h', '--host', default='127.0.0.1'),
            click.option('-p', '--port', default=8000, type=click.INT),
            click.option('--authorization-value', help='Adds this authorization value to the header.'),
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
                authorization_value = options['authorization_value']

                if not options['_from_cws']:
                    sys.argv = [sys.executable, sys.argv[0]]

                class CwsRequestHandler(ChaliceRequestHandler):
                    def _parse_payload(self):
                        headers, body = super()._parse_payload()
                        headers['Authorization'] = authorization_value
                        return headers, body

                class _ThreadedLocalServer(ThreadedLocalServer):

                    def __init__(self):
                        super().__init__(host=options['host'], port=options['port'])
                        self._app_object = self
                        self._config = Config()
                        handler_cls = get_request_handler(authorization_value)
                        self._server = LocalDevServer(command.app, self._config, self._host, self._port,
                                                      handler_cls=handler_cls)

                rc = reloader.run_with_reloader(_ThreadedLocalServer, os.environ, project_dir)
                sys.exit(rc)
            else:
                factory = CwsFactory(command.app, project_dir, debug=debug)
                run_local_server(factory, options['host'], options['port'], workspace)

    def __init__(self, app=None, name='run'):
        super().__init__(app, name=name)
        xray_recorder.configure(context_missing="LOG_ERROR")


class ThreadedLocalServer(Thread):
    """Local threaded server."""

    def __init__(self, *, port=None, host='localhost', authorization_value=None):
        super().__init__()
        self._app_object = None
        self._config = None
        self._host = host
        self._port = port or self.unused_tcp_port()
        self._server = None
        self._server_ready = Event()
        self.handler_cls = get_request_handler(authorization_value)

    def configure(self, app_object, config=None, **kwargs):
        self._app_object = app_object
        self._config = config

    def run(self):
        self._server = LocalDevServer(self._app_object, self._config, self._host, self._port,
                                      handler_cls=self.handler_cls)
        self._server_ready.set()
        self._server.serve_forever()

    def serve_forever(self):
        self._server.serve_forever()

    def shutdown(self):
        if self._server is not None:
            self._server.server.shutdown()

    def make_call(self, method, path, timeout=0.5, **kwarg):
        self._server_ready.wait()
        protocol = "http"
        return method(f'{protocol}://{self._host}:{self._port}{path}', timeout=timeout, **kwarg)

    @classmethod
    def unused_tcp_port(cls):
        with contextlib.closing(socket.socket()) as sock:
            sock.bind(('localhost', 0))
            return sock.getsockname()[1]


def get_request_handler(authorization_value):
    """If an authorization value is defined, the request handler adds it to the header."""

    class CwsRequestHandler(ChaliceRequestHandler):
        def _parse_payload(self):
            headers, body = super()._parse_payload()
            headers['Authorization'] = authorization_value
            return headers, body

    return CwsRequestHandler if authorization_value else ChaliceRequestHandler
