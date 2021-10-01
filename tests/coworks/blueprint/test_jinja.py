from io import BytesIO

from coworks import TechMicroService
from coworks.blueprint.jinja_blueprint import Jinja


class JinjaMS(TechMicroService):

    def __init__(self):
        super().__init__('jinja')
        self.register_blueprint(Jinja())


class TestClass:

    def test_render_empty_template(self):
        app = JinjaMS()
        with app.test_client() as c:
            response = c.post('/render')
            assert response.status_code == 200
            assert response.get_data(as_text=True) == ""
            assert 'Content-Type' in response.headers
            assert response.headers['Content-Type'] == 'text/html; charset=utf-8'

    def test_render_template(self):
        app = JinjaMS()
        with app.test_client() as c:
            data = {
                'template': "hello {{ world_name }}",
                'world_name': "world",
            }
            response = c.get('/render', json=data)
            assert response.status_code == 405
            response = c.post('/render', json=data)
            assert response.status_code == 200
            assert response.get_data(as_text=True) == "hello world"

    def test_render_template_multipart_form(self):
        app = JinjaMS()
        with app.test_client() as c:
            template = BytesIO(b"hello {{ world_name }}")
            form_data = {
                'template': (template, 'template.j2'),
                'world_name': 'world',
            }

            response = c.post('/render', content_type='multipart/form-data', data=form_data)

            assert response.status_code == 200
            assert response.get_data(as_text=True) == "hello world"
