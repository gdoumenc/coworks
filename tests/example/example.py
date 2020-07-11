import os
from collections import defaultdict

import click

from coworks import TechMicroService
from coworks.config import Config
from coworks.cws.command import CwsCommand
from coworks.cws.writer import CwsTerraformWriter


class CwsInfo(CwsCommand):

    @property
    def options(self):
        return (
            *super().options,
            click.option('-h'),
            click.option('-a')
        )

    def _execute(self, options):
        if options['h']:
            self.output.write(f"info passed on {options['h']}")
        else:
            self.output.write(f"info passed on {self.app.ms_name}")


class TechMS(TechMicroService):
    """Technical microservice for the CoWorks tutorial example."""
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
CwsInfo(tech_app, name='info')
CwsTerraformWriter(tech_app)

app = TechMS(configs=Config(environment_variables_file="config/vars_dev.json"))
CwsInfo(tech_app, name='info')

project1 = TechMS()
project2 = TechMS()
