import os
from collections import defaultdict

import click

from coworks import TechMicroService
from coworks.config import Config
from coworks.cws.command import CwsCommand
from coworks.cws.runner import CwsRunner
from coworks.cws.writer import CwsTerraformWriter


class TestCmd(CwsCommand):

    @property
    def options(self):
        return [
            *super().options,
            click.option('-a', '--a', required=True),
            click.option('--b')
        ]

    def _execute(self, *, a, b, **options):
        if a:
            self.output.write(f"test command with a={a}")
            self.output.write("/")
        self.output.write(f"test command with b={b}")


class TechMS(TechMicroService):
    """Technical microservice for the Coworks tutorial example."""
    version = "1.2"
    values = defaultdict(int)
    init_value = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        @self.deferred
        def init(workspace):
            self.init_value = 'test'

    def get(self, usage="test"):
        """Entrypoint for testing named parameter."""
        return f"Simple microservice for {usage}.\n"

    def get_value(self, index):
        """Entrypoint for testing positional parameter."""
        return f"{self.values[index]}\n"

    def put_value(self, index, value=0):
        self.values[index] = value
        return value

    def get_init(self):
        return f"Initial value is {self.init_value}.\n"

    def get_env(self):
        return f"Simple microservice for {os.getenv('test')}.\n"


# usefull for test info (don't remove)
tech_app = TechMS()
TestCmd(tech_app, name='test')
CwsTerraformWriter(tech_app)

app = TechMS(configs=Config(environment_variables_file="config/vars_dev.json"))
TestCmd(tech_app, name='test')


class RunnerMock(CwsRunner):

    def _execute(self, *, project_dir, workspace, host, port, debug, **options):
        assert type(port) is int


project1 = TechMS()
RunnerMock(project1)
project2 = TechMS()
