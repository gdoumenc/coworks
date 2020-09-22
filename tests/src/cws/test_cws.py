import pytest

from coworks.cws.client import client


class TestClass:

    def test_info_wront_project_dir(self, example_dir, capsys):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', 'doesntexist', 'test'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1

    def test_info_no_service(self, example_dir, capsys):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', example_dir, '-m', 'quickstart2', 'cmd'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1

    def test_info_wrong_service(self, example_dir, capsys):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', example_dir, '-m', 'example', '-s', 'test', 'test'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1

    def test_info(self, example_dir, capsys):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', example_dir, '-m', 'example', '-s', 'tech_app', 'test'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == "info passed for b=test info only"

    def test_info_wrong_option(self, example_dir, capsys):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', example_dir, '-m', 'example', '-s', 'tech_app', 'test', '-t', 'wrong'],
                   obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1

    def test_info_right_option(self, example_dir, capsys):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', example_dir, '-m', 'example', '-s', 'tech_app', 'test', '-a', 'right'],
                   obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == "info passed with a=right"

    def test_info_wrong_b_option(self, example_dir, capsys):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', example_dir, '-m', 'example', '-s', 'tech_app', 'test', '-b', 'right'],
                   obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1

    def test_info_right_b_option(self, example_dir, capsys):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', example_dir, '-m', 'example', '-s', 'tech_app', 'test', '--b', 'right'],
                   obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == "info passed for b=right only"

    def test_run(self, example_dir):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', example_dir, '-m', 'example', '-s', 'info', 'run'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1

    def test_export(self, example_dir):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws',
                   args=['-p', example_dir, '-m', 'example', '-s', 'tech_app', 'terraform', '--config', None], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
