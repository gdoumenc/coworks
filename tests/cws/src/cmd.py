import click
from flask.cli import pass_script_info

from coworks.config import Config
from tests.cws.src.app import EnvTechMS


@click.command("test", short_help="Test custom command.")
@click.option('-a', required=True)
@click.option('--b')
@click.pass_context
@pass_script_info
def cmd(info, ctx, a, b):
    app = info.load_app()
    assert app is not None
    assert app.config is not None
    if a:
        print(f"test command with a={a}/", end='')
    print(f"test command with b={b}", end='', flush=True)


app = EnvTechMS()
app_with_conf = EnvTechMS(configs=Config(environment_variables_file="config/vars_dev.json"))
