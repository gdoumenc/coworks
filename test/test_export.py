import pytest

from coworks.tech import OdooMicroService
from coworks.export import TerraformWriter
from .microservice import SimpleMS


def test_export():
    simple = SimpleMS()
    writer = TerraformWriter(simple)
    routes = set(writer.entries.keys())
    assert len(routes) == len(writer.entries.keys())
    assert routes == {'test_root', 'test_kwparam1', 'test_kwparam2', 'test_extended',
                      'test_content', 'test_content__0', 'test_content__0__1', 'test_extended_content', }


@pytest.mark.wip
def test_export_double():
    simple = OdooMicroService(app_name='test')
    writer = TerraformWriter(simple)
    routes = set(writer.entries.keys())
    assert len(routes) == len(writer.entries.keys())
    assert routes == {'test_call', 'test_call__0', 'test_call__0__1',
                      'test_field', 'test_field__0', 'test_field__0__1', 'test_field__0__1__2',
                      'test_id', 'test_id__0', 'test_id__0__1', 'test_id__0__1__2',
                      'test_model', 'test_model__0', 'test_model__0__1'}
