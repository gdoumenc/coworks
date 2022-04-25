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
    def get_wrong(self, i: t.Union[int, str] = 0):
        return ("ok", 200) if type(i) is int else ("not ok", 400)

    @entry
    def post(self, i: t.Union[int, str] = 0):
        return ("ok", 200) if type(i) is int else ("not ok", 400)


class TestClass:

    def test_int_type(self):
        app = TypedMS()

        with app.test_client() as c:
            response = c.get('/1')
            assert response.status_code == 200

            response = c.get('/?i=1')
            assert response.status_code == 200

            response = c.get('/wrong?i=1')
            assert response.status_code == 400

            response = c.post('/', json={'i': 1})
            assert response.status_code == 200

            response = c.post('/', json={'i': '1'})
            assert response.status_code == 400
