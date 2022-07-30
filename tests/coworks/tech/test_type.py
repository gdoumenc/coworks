import typing as t

from coworks import TechMicroService
from coworks import entry


class TypedMS(TechMicroService):

    def _check_token(self):
        """No check."""

    @entry
    def get(self, i: int):
        return ("ok", 200) if type(i) is int else ("not ok", 400)

    @entry
    def get_(self, i: int = 0):
        return ("ok", 200) if type(i) is int else ("not ok", 400)

    @entry
    def get_bool(self, i: bool):
        if type(i) is bool:
            return ("true", 200) if i else ("false", 200)
        return "not ok", 400

    @entry
    def get_bool_(self, i: bool = None):
        if type(i) is bool:
            return ("true", 200) if i else ("false", 200)
        return "not ok", 400

    @entry
    def get_union(self, i: t.Union[int, int] = 0):
        return ("ok", 200) if type(i) is int else ("not ok", 400)

    @entry
    def get_list(self, i: t.List[int] = 0):
        return ("ok", 200) if type(i) is list else ("not ok", 400)

    @entry
    def post(self, i: t.Union[int, int] = 0):
        return ("ok", 200) if type(i) is int else ("not ok", 400)


class TestClass:

    def test_base_type(self):
        app = TypedMS()

        with app.test_client() as c:
            response = c.get('/1')
            assert response.status_code == 200

            response = c.get('/?i=1')
            assert response.status_code == 200

            response = c.post('/', json={'i': 1})
            assert response.status_code == 200

            response = c.post('/', json={'i': '1'})
            assert response.status_code == 200

            response = c.post('/', json={'i': 'abc'})
            assert response.status_code == 400

    def test_bool(self):
        app = TypedMS()

        with app.test_client() as c:
            response = c.get('/bool/true')
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "true"

            response = c.get('/bool/1')
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "true"

            response = c.get('/bool/false')
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "false"

            response = c.get('/bool/0')
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "false"

            response = c.get('/bool?i=true')
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "true"

            response = c.get('/bool?i=1')
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "true"

            response = c.get('/bool?i=false')
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "false"

            response = c.get('/bool?i=0')
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "false"

    def test_union_type(self):
        app = TypedMS()

        with app.test_client() as c:
            response = c.get('/union?i=1')
            assert response.status_code == 200

            response = c.get('/union?i=1&i=2')
            assert response.status_code == 400

            response = c.get('/union?i=abc')
            assert response.status_code == 400

    def test_list_type(self):
        app = TypedMS()

        with app.test_client() as c:
            response = c.get('/list?i=1')
            assert response.status_code == 200

            response = c.get('/list?i=1&i=2')
            assert response.status_code == 200

            response = c.get('/list?i=abc')
            assert response.status_code == 400
