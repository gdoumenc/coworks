import os
import shutil

import pytest

from coworks.cli.client import client


def test_init():
    chalice_dir = os.path.join('test', '.chalice')
    shutil.rmtree(chalice_dir)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        client(prog_name='cws', args=['-p', 'test', 'init'], obj={})
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0

    assert os.path.exists(chalice_dir)
    assert os.path.exists(f"{chalice_dir}/config.json")


def test_info():
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        client(prog_name='cws', args=['-p', 'test/example', 'info'], obj={})
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        client(prog_name='cws', args=['-p', 'test/example', 'info', '-m', 'example'], obj={})
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        client(prog_name='cws', args=['-p', 'test/example', 'info', '-m', 'example', '-a', 'tech_app'], obj={})
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0


def test_export():
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        client(prog_name='cws', args=['-p', 'test/example', 'export', '-m', 'example', '-a', 'tech_app'], obj={})
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0
