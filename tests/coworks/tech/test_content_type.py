from coworks import TechMicroService
from coworks import entry


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
            assert not response.is_json
            assert response.headers['Content-Type'] == 'text/plain'
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
            assert not response.is_json
            assert response.headers['Content-Type'] == 'text/plain'
            assert response.get_data(as_text=True) == '{"int":1,"text":"value"}\n'
