import contextlib
import socket
from threading import Thread, Event

from chalice.config import Config
from chalice.local import LocalDevServer


class ThreadedLocalServer(Thread):
    threaded_servers = {}

    def __init__(self, *, port=None, host='localhost'):
        super(ThreadedLocalServer, self).__init__()
        self._app_object = None
        self._config = None
        self._host = host
        self._port = port or self.unused_tcp_port()
        self._server = None
        self._server_ready = Event()

    def wait_for_server_ready(self):
        self._server_ready.wait()

    def configure(self, app_object, config=None):
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
