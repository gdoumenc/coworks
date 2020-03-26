import io
import re

import yaml
from coworks.export import ListWriter, OpenApiWriter, TerraformWriter

from .tech_ms import SimpleMS


def test_export_list():
    simple = SimpleMS()
    writer = ListWriter(simple)
    simple.extensions['writers']['list'].export(output='/dev/null')
    output = io.StringIO()
    writer.export(output=output)
    output.seek(0)
    assert re.sub(r"\s", "",
                  output.read()) == "//content/content/{_0}/content/{_0}/{_1}/extended/content/kwparam1/kwparam2"


def test_export_open_api():
    simple = SimpleMS()
    writer = OpenApiWriter(simple)
    simple.extensions['writers']['openapi'].export(output='/dev/null')
    output = io.StringIO()
    writer.export(output=output)
    output.seek(0)
    print(output.read())
    output.seek(0)
    data = yaml.load(output)
    assert {'info', 'openapi', 'paths', 'version'} == set(data.keys())
    assert {'/', '/content', '/content/{_0}', '/content/{_0}/{_1}', '/extended/content', '/kwparam1',
            '/kwparam2'} == set(data['paths'].keys())


def test_export_terraform():
    simple = SimpleMS()
    writer = TerraformWriter(simple)
    simple.extensions['writers']['terraform'].export(output='/dev/null')
    output = io.StringIO()
    writer.export(output=output)
    output.seek(0)
    print(output.read())
    output.seek(0)
    assert len(re.sub(r"\s", "", output.read())) == 1973

# def test_export_terraform_double():
#     simple = OdooMicroService(app_name='test')
#     writer = TerraformWriter(simple)
#     routes = set(writer.entries.keys())
#     assert len(routes) == len(writer.entries.keys())
#     assert routes == {'test_call', 'test_call__0', 'test_call__0__1',
#                       'test_field', 'test_field__0', 'test_field__0__1', 'test_field__0__1__2',
#                       'test_id', 'test_id__0', 'test_id__0__1', 'test_id__0__1__2',
#                       'test_model', 'test_model__0', 'test_model__0__1'}
