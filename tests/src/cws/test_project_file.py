import pytest

from coworks.cws.client import client, ProjectConfig


class TestClass:
    def test_no_project_file_no_module(self, example_dir, capsys):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', 'tests', 'test'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1

    def test_project_file_no_param(self, example_dir, capsys):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', 'tests/example', 'test'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == \
               "test command with a=default/test command with b=valuetest command with a=project2/test command with b=value"

    def test_project_file_no_param_workspace_dev(self, example_dir, capsys):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', 'tests/example', '-w', 'dev', 'test'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == \
               "test command with a=default/test command with b=valuetest command with a=project2/test command with b=value"

    def test_project_file_no_param_workspace_prod(self, example_dir, capsys):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', 'tests/example', '-w', 'prod', 'test'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == \
               "test command with a=default/test command with b=valuetest command with a=prod2/test command with b=value"

    def test_project_file_param(self, example_dir, capsys):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', 'tests/example', 'test', '-a', 'param'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == \
               "test command with a=param/test command with b=valuetest command with a=param/test command with b=value"

    def test_project_file_project1(self, example_dir, capsys):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', 'tests/example', '-m', 'example', '-s', 'project1', 'test'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == "test command with a=default/test command with b=value"

    def test_project_file_project2(self, example_dir, capsys):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            client(prog_name='cws', args=['-p', 'tests/example', '-m', 'example', '-s', 'project2', 'test'], obj={})
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
        captured = capsys.readouterr()
        assert captured.out == "test command with a=project2/test command with b=value"

    def test_all_services(self):
        conf = ProjectConfig('tests/src/cws')
        services = conf.all_services()
        assert len(services) == 3
        assert ('m1', 's1') in services
        assert ('m1', 's2') in services
        assert ('m1', 's3') not in services
        assert ('m2', 's3') in services

    def test_command0(self):
        conf = ProjectConfig('tests/src/cws')
        service_conf = conf.get_service_config('module', 'service', 'dev')
        commands = conf.all_commands
        assert len(commands) == 4
        options = service_conf.get_command_options('test_command0')
        assert len(options) == 7
        assert options['option_key1'] == "option_value1"
        assert options['option_key2'] == "option_value2"
        assert options['option_key3'] == "option_value3"

    def test_command1(self):
        conf = ProjectConfig('tests/src/cws')
        service_conf = conf.get_service_config('module', 'service', 'dev')
        options = service_conf.get_command_options('test_command1')
        assert len(options) == 7
        assert options['option_key1'] == "option_value1"
        assert options['option_key2'] == "option_value2"
        assert options['option_key3'] == "option_value5"
        service_conf = conf.get_service_config('module', 'service', 'prod')
        options = service_conf.get_command_options('test_command1')
        assert len(options) == 7
        assert options['option_key1'] == "option_value1"
        assert options['option_key2'] == "option_value4"
        assert options['option_key3'] == "option_value5"

    def test_command2_no_service(self):
        conf = ProjectConfig('tests/src/cws')
        service_conf = conf.get_service_config('module', 'service', 'dev')
        options = service_conf.get_command_options('test_command2')
        assert len(options) == 6
        assert options['option_key1'] == "option_value1"
        assert options['option_key2'] == "option_value2"

    def test_command2_wrong_service(self):
        conf = ProjectConfig('tests/src/cws')
        service_conf = conf.get_service_config('m1', 'service', 'dev')
        options = service_conf.get_command_options('test_command2')
        assert len(options) == 7
        assert options['option_key1'] == "option_value1"
        assert options['option_key2'] == "option_value4"
        assert options['option_key4'] == "option_value8"
        service_conf = conf.get_service_config('m1', 'service', 'prod')
        options = service_conf.get_command_options('test_command2')
        assert len(options) == 6
        assert options['option_key1'] == "option_value1"
        assert options['option_key2'] == "option_value4"

    def test_command2_service_s1(self):
        conf = ProjectConfig('tests/src/cws')
        service_conf = conf.get_service_config('m1', 's1', 'dev')
        options = service_conf.get_command_options('test_command2')
        assert len(options) == 8
        assert options['option_key1'] == "option_value1"
        assert options['option_key2'] == "option_value4"
        assert options['option_key3'] == "option_value5"
        assert options['option_key4'] == "option_value8"
        service_conf = conf.get_service_config('m1', 's1', 'prod')
        options = service_conf.get_command_options('test_command2')
        assert len(options) == 7
        assert options['option_key1'] == "option_value1"
        assert options['option_key2'] == "option_value4"
        assert options['option_key3'] == "option_value5"
        assert 'option_key4' not in options

    def test_command2_service_s2(self):
        conf = ProjectConfig('tests/src/cws')
        service_conf = conf.get_service_config('m1', 's2', 'dev')
        options = service_conf.get_command_options('test_command2')
        assert len(options) == 7
        assert options['option_key1'] == "option_value1"
        assert options['option_key2'] == "option_value4"
        assert options['option_key4'] == "option_value7"
        service_conf = conf.get_service_config('m1', 's2', 'prod')
        options = service_conf.get_command_options('test_command2')
        assert len(options) == 7
        assert options['option_key1'] == "option_value1"
        assert options['option_key2'] == "option_value4"
        assert options['option_key4'] == "option_value6"
