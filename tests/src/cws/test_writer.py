import functools
import io
import re
import pytest

import yaml

from coworks.cws import TerraformWriter
from coworks.cws.writer.writer import ListWriter, OpenApiWriter
from tests.src.coworks.tech_ms import SimpleMS


def test_export_list():
    simple = SimpleMS()
    writer = ListWriter(simple)
    simple.extensions['writers']['list'].export(output='/dev/null')
    output = io.StringIO()
    writer.export(output=output)
    output.seek(0)
    assert len(output.read()) == 83


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
    print(writer.pathes)
    assert len(writer.pathes) == 7
    sum = lambda x, y: x + y
    print([e.keys() for e in writer.pathes.values()])
    assert functools.reduce(sum, [len(e.keys()) for e in writer.pathes.values()], 0) == 9


def test_export_terraform():
    simple = SimpleMS()
    writer = TerraformWriter(simple)
    simple.extensions['writers']['terraform'].export(output='/dev/null')
    output = io.StringIO()
    writer.export(output=output)
    output.seek(0)
    print(output.read())
    output.seek(0)
    assert len(re.sub(r"\s", "", output.read())) == 18226
    print(writer.entries)
    assert len(writer.entries) == 8

    assert writer.entries['_'].parent_uid is None
    assert writer.entries['_'].is_root
    assert writer.entries['_'].path is None
    assert 'GET' in writer.entries['_'].methods
    assert 'POST' not in writer.entries['_'].methods

    assert writer.entries['__content'].parent_uid == '_'
    assert not writer.entries['__content'].is_root
    assert writer.entries['__content'].parent_is_root
    assert writer.entries['__content'].path == 'content'
    assert 'GET' in writer.entries['__content'].methods
    assert 'POST' in writer.entries['__content'].methods

    assert writer.entries['__extended'].methods is None

    assert not writer.entries['__extended_content'].is_root
    assert not writer.entries['__extended_content'].parent_is_root
    assert 'GET' in writer.entries['__extended_content'].methods

