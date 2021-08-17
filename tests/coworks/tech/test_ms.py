from coworks.coworks import CoworksResponse
from tests.coworks.ms import *


class ParamMS(TechMicroService):
    value = "123"

    @entry
    def get(self, str):
        return str

    @entry
    def get_concat(self, str1, str2):
        return str1 + str2

    @entry
    def get_value(self):
        return self.value

    @entry
    def put_value(self, value=None):
        self.value = value
        return self.value

    @entry
    def get_param(self, str1, param1='default1', param2='default2'):
        return str1 + str(param1) + param2


class TupleReturnedMS(TechMS):
    @entry
    def get(self):
        return 'ok', 200

    @entry
    def get_json(self):
        return {'value': 'ok'}, 200

    @entry
    def get_resp(self, str):
        return CoworksResponse(str, 200)

    @entry
    def get_error(self, str):
        return str, 300

    @entry
    def get_tuple(self, str):
        return str, 200, {'x-test': 'true'}


class AmbiguousMS(TechMS):
    @entry
    def get(self, uid):
        return uid, 200

    @entry
    def post_test(self):
        return {'value': 'ok'}, 200


class TestClass:
    def test_request_arg(self):
        app = SimpleMS()
        with app.test_client() as c:
            response = c.get('/')
            assert response.status_code == 200
            assert response.text == "get"
            assert 'Content-Type' in response.headers
            assert response.headers['Content-Type'] == 'application/json'
            assert 'Content-Length' in response.headers
            assert response.headers['Content-Length'] == str(len(response.text))
            response = c.post('/')
            assert response.status_code == 405
            response = c.get('/get1')
            assert response.status_code == 404
            response = c.get('/content')
            assert response.status_code == 200
            assert response.text == "get content"
            response = c.get('/content/3')
            assert response.status_code == 200
            assert response.text == "get content with 3"
            response = c.get('/content/3/other')
            assert response.status_code == 200
            assert response.text == "get content with 3 and other"
            response = c.post('/content', json={"other": 'other'})
            assert response.status_code == 200
            assert response.text == "post content without value but other"
            response = c.post('/content/3', json={"other": 'other'})
            assert response.status_code == 200
            assert response.text == "post content with 3 and other"
            response = c.post('/content/3', json="other")
            assert response.status_code == 200
            assert response.text == "post content with 3 and other"
            response = c.post('/content/3', json={"other": 'other', "value": 5})
            assert response.status_code == 400

    def test_request_kwargs(self):
        app = SimpleMS()
        with app.test_client() as c:
            response = c.get('/kwparam1?value=5')
            assert response.status_code == 200
            assert response.text == "get **param with only 5"
            response = c.get('/kwparam1', params={"other": 'other', "value": 5})
            assert response.status_code == 400
            response = c.get('/kwparam1', params={"value": 5})
            assert response.status_code == 200
            assert response.text == "get **param with only 5"
            response = c.get('/kwparam1', json={"other": 'other', "value": 5})
            assert response.status_code == 200
            assert response.text == "get **param with only 0"
            response = c.get('/kwparam2', params={"other": 'other', "value": 5})
            assert response.status_code == 200
            assert response.text == "get **param with 5 and ['other']"
            response = c.get('/kwparam2', json={"other": 'other', "value": 5})
            assert response.status_code == 200
            assert response.text == "get **param with 0 and []"
            response = c.put('/kwparam2', json={"other": 'other', "value": 5})
            assert response.status_code == 200
            assert response.text == "get **param with 5 and ['other']"
            response = c.put('/kwparam2', params={"other": 'other', "value": 5})
            assert response.status_code == 200
            assert response.text == "get **param with None and []"

            response = c.get('/extended/content')
            assert response.status_code == 200
            assert response.text == "hello world"

    def test_parameterized(self):
        app = ParamMS()
        with app.test_client() as c:
            response = c.get('/123')
            assert response.status_code == 200
            assert response.text == '123'
            response = c.get('/concat/123/456')
            assert response.status_code == 200
            assert response.text == '123456'
            response = c.get('/value')
            assert response.status_code == 200
            assert response.text == '123'
            response = c.put("/value", json={'value': "456"})
            assert response.status_code == 200
            assert response.text == '456'
            response = c.get("/value")
            assert response.status_code == 200
            assert response.text == '456'
            response = c.get('/param/test1')
            assert response.status_code == 200
            assert response.text == 'test1default1default2'
            response = c.get('/param/test1', params={'param1': "value1"})
            assert response.status_code == 200
            assert response.text == 'test1value1default2'
            response = c.get('/param/test1', params={'param2': "value2"})
            assert response.status_code == 200
            assert response.text == 'test1default1value2'
            response = c.get('/param/test1', params={'param1': "param1", 'param2': "param2"})
            assert response.status_code == 200
            assert response.text == 'test1param1param2'
            response = c.get('/param/test1', params={'param1': ['value1', 'value2']})
            assert response.status_code == 200
            assert response.text == "test1['value1', 'value2']default2"

    def test_slug_parameterized(self):
        app = ParamMS()
        with app.test_client() as c:
            response = c.get('/123')
            assert response.status_code == 200
            assert response.text == '123'
            response = c.get('/concat/123/456')
            assert response.status_code == 200
            assert response.text == '123456'

    def test_tuple_returned(self):
        app = TupleReturnedMS()
        with app.test_client() as c:
            headers = {'Content-type': 'text/plain', 'Accept': 'text/plain'}
            response = c.get('/', headers=headers)
            assert response.status_code == 200
            assert response.text == 'ok'
            assert response.headers['content-type'] == 'application/json'
            response = c.get('/json')
            assert response.status_code == 200
            assert response.json['value'] == 'ok'
            assert response.headers['content-type'] == 'application/json'
            response = c.get('/resp/ok')
            assert response.status_code == 200
            assert response.text == 'ok'
            assert response.headers['content-type'] == 'application/json'
            response = c.get('/tuple/test')
            assert response.status_code == 200
            assert response.headers['content-type'] == 'application/json'
            assert response.headers['x-test'] == 'true'
            assert response.text == 'test'

    def test_entry_not_unique(self):
        app = AmbiguousMS()
        with app.app_context():
            assert '/test' in app.routes
        with app.test_client() as c:
            response = c.get('/123')
            assert response.status_code == 200
            assert response.text == '123'
            response = c.post('/test')
            assert response.status_code == 200
            assert response.json == {'value': "ok"}
