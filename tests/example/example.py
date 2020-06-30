import os
from collections import defaultdict

import click

from coworks import TechMicroService
from coworks.cws import CwsProject
from coworks.cws.command import CwsCommand


class CwsInfo(CwsCommand):

    @property
    def options(self):
        return (click.option('-h'),)

    def _execute(self, **kwargs):
        self.output.write('info passed')


class TechMS(TechMicroService):
    """Technical microservice for the CoWorks tutorial example."""
    version = "1.2"
    values = defaultdict(int)

    def get(self, usage="test"):
        """Entrypoint for testing named parameter."""
        return f"Simple microservice for {usage}.\n"

    def get_value(self, index):
        """Entrypoint for testing positional parameter."""
        return f"{self.values[index]}\n"

    def put_value(self, index, value=0):
        self.values[index] = value
        return value

    def get_env(self):
        return f"Simple microservice for {os.getenv('test')}.\n"


# usefull for test info (don't remove)
tech_app = TechMS()
CwsProject(tech_app)
CwsInfo(tech_app, name='info')

app = TechMS()
CwsProject(app)
