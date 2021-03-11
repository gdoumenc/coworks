from unittest.mock import Mock

import click
import pytest

from coworks.cws.command import CwsCommand, CwsCommandError
from tests.coworks.tech_ms import *

cmd_mock = Mock()


class MyCommand(CwsCommand):
    def multi_execute(cls, project_dir, workspace, execution_list):
        cmd_mock()
        for command, options in execution_list:
            assert project_dir == 'tests/cws'
            assert options['module'] == 'test_cmd'
            assert options['workspace'] == 'dev'
            assert options['service'] == 'test'


class MyCommandWithOptions(MyCommand):

    @property
    def options(self):
        return [
            *super().options,
            click.option('--param', required=True),
            click.option('--other', required=True),
            click.option('--nothing'),
        ]


class TestCommand:

    def test_command(self):
        simple = SimpleMS()
        MyCommand(simple, name='test')

        with pytest.raises(CwsCommandError) as pytest_wrapped_e:
            simple.execute('autre', project_dir='tests/cws', module='test_cmd', workspace='dev')
        assert pytest_wrapped_e.type == CwsCommandError
        assert pytest_wrapped_e.value.msg == 'The command autre was not added to the microservice test.\n'

        simple.execute('test', project_dir='tests/cws', module='test_cmd', workspace='dev')
        cmd_mock.assert_called_once()

        simple.execute('test', project_dir='tests/cws', module='test_cmd', workspace='dev', help=None)

    def test_command_with_options(self):
        simple = SimpleMS()
        MyCommandWithOptions(simple, name='test_command_with_options')

        with pytest.raises(CwsCommandError) as pytest_wrapped_e:
            simple.execute('test_command_with_options', project_dir='tests/cws', module='test_cmd', workspace='dev')
        assert pytest_wrapped_e.type == CwsCommandError
        assert pytest_wrapped_e.value.msg == 'missing parameter: param'

        simple.execute('test_command_with_options', project_dir='tests/cws', module='test_cmd', workspace='dev',
                       param='param', other='other')
