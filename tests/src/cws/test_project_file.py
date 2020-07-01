import pytest

from coworks.cws.client import client


class TestClass:

    def test_no_project_file_no_module(self, example_dir, capsys):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', 'tests', 'test'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1

    @pytest.mark.wip
    def test_project_file_no_param(self, example_dir, capsys):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', 'tests/example', 'test'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == "info passed on test infoinfo passed on project2"
