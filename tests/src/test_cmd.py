from collections import defaultdict

import click
import os
from flask.cli import pass_script_info

from coworks import TechMicroService, entry
from coworks.config import Config


@click.command("test", short_help="Test custom command.")
@click.option('-a', required=True)
@click.option('--b')
@click.pass_context
@pass_script_info
def test_cmd(info, ctx, a, b):
    app = info.load_app()
    assert app is not None
    assert app.config is not None
    if a:
        print(f"test command with a={a}/", end='')
    print(f"test command with b={b}", end='', flush=True)


class ExampleMS(TechMicroService):
    version = "1.2"
    values = defaultdict(int)
    init_value = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # @self.deferred
        #     def init(workspace):
        # self.init_value = 'test'

    @entry
    def get(self, usage="test"):
        """Entrypoint for testing named parameter."""
        return f"Simple microservice for {usage}.\n"

    @entry
    def get_value(self, index):
        """Entrypoint for testing positional parameter."""
        return f"{self.values[index]}\n"

    @entry
    def put_value(self, index, value=0):
        self.values[index] = value
        return value

    @entry
    def get_init(self):
        return f"Initial value is {self.init_value}.\n"

    @entry
    def get_env(self):
        return f"Simple microservice for {os.getenv('test')}.\n"


app1 = ExampleMS()
app2 = ExampleMS(configs=Config(environment_variables_file="config/vars_dev.json"))
