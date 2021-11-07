from coworks.coworks import ApiResponse
from tests.coworks.ms import *


class ParamMS(TechMicroService):
    value = "123"

    def token_authorizer(self, token):
        return True

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

    @entry
    def post_params(self, **kwargs):
        return {
            'keys': [k for k in kwargs.keys()],
        }


class TupleReturnedMS(TechMS):

    @entry
    def get(self):
        return 'ok', 200

    @entry
    def get_json(self):
        return {'value': 'ok'}, 200

    @entry
    def get_resp(self, str):
        return ApiResponse(str, 200)

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
            response = c.get('/', headers={'Accept': 'text/plain', 'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "get"
            assert 'Content-Type' in response.headers
            assert response.headers['Content-Type'] == 'application/json'
            assert 'Content-Length' in response.headers
            assert response.headers['Content-Length'] == str(len(response.get_data(as_text=True)))
            response = c.post('/', headers={'Authorization': 'token'})
            assert response.status_code == 405
            response = c.get('/get1', headers={'Authorization': 'token'})
            assert response.status_code == 404
            response = c.get('/content', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "get content"
            response = c.get('/content/3', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "get content with 3"
            response = c.get('/content/3/other', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "get content with 3 and other"
            response = c.post('/content', json={"other": 'other'}, headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "post content without value but other"
            response = c.post('/content/3', json={"other": 'other'}, headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "post content with 3 and other"
            response = c.post('/content/3', json="other", headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "post content with 3 and other"
            response = c.post('/content/3', json={"other": 'other', "value": 5}, headers={'Authorization': 'token'})
            assert response.status_code == 400

    def test_request_kwargs(self):
        app = SimpleMS()
        with app.test_client() as c:
            response = c.get('/kwparam1?value=5', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "get **param with only 5"
            response = c.get('/kwparam1?other=other&value=5', headers={'Authorization': 'token'})
            assert response.status_code == 400
            response = c.get('/kwparam1?value=5', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "get **param with only 5"
            response = c.get('/kwparam1', json={"other": 'other', "value": 5}, headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "get **param with only 0"
            response = c.get('/kwparam2?other=other&value=5', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "get **param with 5 and ['other']"
            response = c.get('/kwparam2', json={"other": 'other', "value": 5}, headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "get **param with 0 and []"
            response = c.put('/kwparam2', json={"other": 'other', "value": 5}, headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "get **param with 5 and ['other']"
            response = c.put('/kwparam2?other=other&value=5', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "get **param with 5 and ['other']"

            response = c.get('/extended/content', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "hello world"

    def test_request_form_data(self):
        """normal API call."""
        app = ParamMS()
        with app.test_client() as c:
            files = {
                'template': io.BytesIO(b"hello {{ world_name }}"),
            }
            data = {
                'key': 'value',
                'template': (files['template'], 'template.j2'),
            }

            response = c.post('/params', content_type='multipart/form-data', data=data,
                              headers={'Authorization': 'token'})

            assert response.status_code == 200
            assert response.is_json
            assert 'keys' in response.json
            assert response.json['keys'] == ['key', 'template']

    def test_parameterized(self):
        app = ParamMS()
        with app.test_client() as c:
            response = c.get('/123', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == '123'
            response = c.get('/concat/123/456', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == '123456'
            response = c.get('/value', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == '123'
            response = c.put("/value", json={'value': "456"}, headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == '456'
            response = c.get("/value", headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == '456'
            response = c.get('/param/test1', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == 'test1default1default2'
            response = c.get('/param/test1?param1=value1', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == 'test1value1default2'
            response = c.get('/param/test1?param2=value2', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == 'test1default1value2'
            response = c.get('/param/test1?param1=value1&param2=value2', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == 'test1value1value2'
            response = c.get('/param/test1?param1=value1&param1=value2', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "test1['value1', 'value2']default2"

    def test_slug_parameterized(self):
        app = ParamMS()
        with app.test_client() as c:
            response = c.get('/123', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == '123'
            response = c.get('/concat/123/456', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == '123456'

    def test_tuple_returned(self):
        app = TupleReturnedMS()
        with app.test_client() as c:
            headers = {'Accept': 'text/plain', 'Authorization': 'token'}
            response = c.get('/', headers=headers)
            assert response.status_code == 200
            assert response.get_data(as_text=True) == 'ok'
            assert response.headers['content-type'] == 'application/json'
            response = c.get('/json', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.json['value'] == 'ok'
            assert response.headers['content-type'] == 'application/json'
            response = c.get('/resp/ok', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == 'ok'
            assert response.headers['content-type'] == 'application/json'
            response = c.get('/tuple/test', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.headers['content-type'] == 'application/json'
            assert response.headers['x-test'] == 'true'
            assert response.get_data(as_text=True) == 'test'

    def test_entry_not_unique(self):
        app = AmbiguousMS()
        with app.test_request_context():
            assert '/test' in app.routes
        with app.test_client() as c:
            response = c.get('/123', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.get_data(as_text=True) == '123'
            response = c.post('/test', headers={'Authorization': 'token'})
            assert response.status_code == 200
            assert response.json == {'value': "ok"}
