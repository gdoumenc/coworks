import pytest

from coworks import Blueprint
from coworks import TechMicroService
from coworks import entry


class BP(Blueprint):

    @entry
    def get_entry(self):
        return f"blueprint test entry"


class MS(TechMicroService):

    @entry
    def get_bp_entry(self):
        return f"blueprint test entry"


class TestClass:

    def test_overload(self):
        app = MS()
        app.register_blueprint(BP(), url_prefix='bp')
        with pytest.raises(AssertionError) as pytest_wrapped_e:
            with app.test_client() as c:
                response = c.get('/', headers={'Authorization': 'token'})
        assert pytest_wrapped_e.type == AssertionError
