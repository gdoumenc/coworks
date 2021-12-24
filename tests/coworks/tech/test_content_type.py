from coworks import TechMicroService
from coworks import entry

from ..event import get_event


class ContentMS(TechMicroService):

    @entry
    def get(self):
        return "test"

    @entry
    def get_json(self):
        return {'text': 'value', 'int': 1}

    @entry
    def post(self, text=None, context=None, files=None):
        if files:
            if type(files) is not list:
                files = [files]
            return f"post {text}, {context} and {[f.file.name for f in files]}"
        return f"post {text}, {context}"

    @entry(binary=True)
    def get_binary(self):
        return b"test"

    @entry(binary=True, content_type='application/pdf')
    def get_content_type(self):
        return b"test"

    @entry(binary=True, no_auth=True)
    def get_no_auth(self):
        return b"test"


class TestClass:
    def test_default_content_type(self):
        app = ContentMS()
        with app.test_client() as c:
            headers = {'Authorization': 'token'}
            response = c.get('/', headers=headers)
            assert response.status_code == 200
            assert response.is_json
            assert response.headers['Content-Type'] == 'application/json'
            assert response.get_data(as_text=True) == 'test'

    def test_json_content_type(self):
        app = ContentMS()
        with app.test_client() as c:
            headers = {'Accept': 'application/json', 'Authorization': 'token'}
            response = c.get('/', headers=headers)
            assert response.status_code == 200
            assert response.is_json
            assert response.headers['Content-Type'] == 'application/json'
            assert response.get_data(as_text=True) == 'test'

    def test_text_content_type(self):
        app = ContentMS()
        with app.test_client() as c:
            headers = {'Accept': 'text/plain', 'Authorization': 'token'}
            response = c.get('/', headers=headers)
            assert response.status_code == 200
            assert response.is_json
            assert response.headers['Content-Type'] == 'application/json'
            assert response.get_data(as_text=True) == 'test'

    def test_text_api(self):
        app = ContentMS()
        with app.test_client() as c:
            headers = {'Authorization': 'token'}
            response = c.get('/json', headers=headers)
            assert response.status_code == 200
            assert response.is_json
            assert response.headers['Content-Type'] == 'application/json'
            assert response.json == {"int": 1, "text": "value"}

            headers = {'Accept': 'application/json', 'Authorization': 'token'}
            response = c.get('/json', headers=headers)
            assert response.status_code == 200
            assert response.is_json
            assert response.headers['Content-Type'] == 'application/json'
            assert response.json == {"int": 1, "text": "value"}

            headers = {'Accept': 'text/plain', 'Authorization': 'token'}
            response = c.get('/json', headers=headers)
            assert response.status_code == 200
            assert response.is_json
            assert response.headers['Content-Type'] == 'application/json'
            assert response.get_data(as_text=True) == '{"int":1,"text":"value"}\n'

    def test_binary_content_type(self, empty_context):
        app = ContentMS()
        with app.test_client() as c:
            headers = {'Accept': 'img/webp', 'Authorization': 'token'}
            response = app(get_event('/binary', 'get', headers=headers), empty_context)
            assert type(response) == str
            assert app.base64decode(response) == b"test"

    def test_content_type(self, empty_context):
        app = ContentMS()
        with app.test_client() as c:
            headers = {'Accept': 'img/webp', 'Authorization': 'token'}
            response = app(get_event('/content/type', 'get', headers=headers), empty_context)
            assert type(response) == str
            assert app.base64decode(response) == b"test"

