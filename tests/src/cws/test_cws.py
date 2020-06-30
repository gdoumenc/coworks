import pytest

from coworks.cws.client import client


class TestClass:

    def test_info(self, example_dir):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', 'doesntexist', 'info'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1

        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', example_dir, 'info'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1

        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', example_dir, '-m', 'quickstart2', 'info'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 2

        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', example_dir, '-m', 'example', '-s', 'test', 'info'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1

        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', example_dir, '-m', 'example', '-s', 'tech_app', 'info'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0

        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', example_dir, '-m', 'example', '-s', 'tech_app', 'info', '-t', 'wrong'],
                   obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 2

        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', example_dir, '-m', 'example', '-s', 'tech_app', 'info', '-h', 'right'],
                   obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0

    def test_run(self, example_dir):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', example_dir, '-m', 'example', '-s', 'info', 'run'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1

    def test_export(self, example_dir):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', example_dir, '-m', 'example', '-s', 'tech_app', 'export'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
