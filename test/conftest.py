import pytest

from .local_server import ThreadedLocalServer


@pytest.fixture()
def local_server_factory():
    threaded_server = ThreadedLocalServer()

    def create_server(app):
        threaded_server.configure(app)
        threaded_server.start()
        return threaded_server

    try:
        yield create_server
    finally:
        threaded_server.shutdown()
