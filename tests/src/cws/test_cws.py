import io
import json
import os
import shutil

import pytest

from coworks.cws.client import client

EXAMPLE_DIR = os.getenv('EXAMPLE_DIR')


def test_init():
    chalice_dir = os.path.join('test', '.chalice')
    if os.path.exists(chalice_dir):
        shutil.rmtree(chalice_dir)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        client(prog_name='cws', args=['-p', 'test', 'init'], obj={})
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0

    assert os.path.exists(chalice_dir)
    assert os.path.exists(f"{chalice_dir}/config.json")

    shutil.rmtree(chalice_dir)


def test_info():
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        client(prog_name='cws', args=['-p', EXAMPLE_DIR, 'info'], obj={})
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        client(prog_name='cws', args=['-p', EXAMPLE_DIR, 'info', '-m', 'quickstart2'], obj={})
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        output = io.StringIO()
        client(prog_name='cws', args=['-p', EXAMPLE_DIR, 'info', '-m', 'quickstart2', '-o', output], obj={})
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0
    output.seek(0)
    out = json.loads(output.read())
    assert 'name' in out
    assert out['name'] == "test"
    assert 'type' in out
    assert out['type'] == "tech"

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        client(prog_name='cws', args=['-p', EXAMPLE_DIR, 'info', '-m', 'example', '-a', 'test'], obj={})
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        client(prog_name='cws', args=['-p', EXAMPLE_DIR, 'info', '-m', 'example', '-a', 'tech_app'], obj={})
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0


def test_export():
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        client(prog_name='cws', args=['-p', EXAMPLE_DIR, 'export', '-m', 'example', '-a', 'tech_app'], obj={})
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0
