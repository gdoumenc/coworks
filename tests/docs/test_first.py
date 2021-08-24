import requests
import threading
import time

from coworks.utils import import_attr


class TestClass:

    def test_run_first(self, samples_docs_dir, unused_tcp_port):
        app = import_attr('first', 'app', cwd=samples_docs_dir)
        server = threading.Thread(target=run_server_quickstart, args=(app, unused_tcp_port), daemon=True)
        server.start()
        counter = 1
        time.sleep(counter)
        while not server.is_alive() and counter < 10:
            time.sleep(counter)
            counter += 1
        response = requests.get(f'http://localhost:{unused_tcp_port}/', headers={'Authorization': "token"})
        assert response.text == "Stored value 0.\n"
        response = requests.post(f'http://localhost:{unused_tcp_port}/', json={'value': 1},
                                 headers={'Authorization': "token"})
        assert response.text == "Value stored (1).\n"
        response = requests.get(f'http://localhost:{unused_tcp_port}/', headers={'Authorization': "token"})
        assert response.text == "Stored value 1.\n"


def run_server_quickstart(app, port):
    print(f"Server starting on port {port}")
    app.run(host='localhost', port=port, debug=False)
