import click
from flask.cli import pass_script_info

from tests.cws.src.app import EnvTechMS


@click.command("test", short_help="Test custom command.")
@click.option('-a', required=True)
@click.option('--b')
@click.pass_context
@pass_script_info
def cmd(info, ctx, a, b):
    cws_app = info.load_app()
    assert cws_app is not None
    assert cws_app.config is not None
    if a:
        print(f"test command with a={a}/", end='')
    print(f"test command with b={b}", end='', flush=True)


@click.command("test", short_help="Test custom command.")
@click.option('-a', required=True)
@click.option('--b')
@click.pass_context
@pass_script_info
def cmd1(info, ctx, a, b):
    cws_app = info.load_app()
    assert cws_app is not None
    assert cws_app.config is not None
    if a:
        print(f"test command v1 with a={a}/", end='')
    print(f"test command v1 with b={b}", end='', flush=True)


app = EnvTechMS()
