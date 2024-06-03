import sys
import typing as t
from pathlib import Path
from shutil import copytree

import click
from jinja2 import Environment
from jinja2 import PackageLoader
from jinja2 import select_autoescape

from coworks.version import __version__
from .command import CwsCommand
from .command import no_project_context


@click.command("new", CwsCommand, short_help="Creates a new CoWorks project.")
@click.option('--dir', '-d', default='.', help="Directory where the projet will be created.")
@click.option('--force', '-f', is_flag=True, help="Force creation even if already created.")
@no_project_context
def new_command(dir, force) -> None:
    project_templates = Path(__file__).parent / 'project_templates'

    # Copy project configuration file
    dest = Path(dir)
    project_conf = dest / "project.cws.yml"

    if project_conf.exists() and not force:
        click.echo(f"Project was already created in {dest}. Set 'force' option for recreation.")
        return

    # Copy files
    copytree(src=project_templates.as_posix(), dst=dest, dirs_exist_ok=True)
    (dest / 'template.env').rename('.env')

    # Render project configuration file
    template_loader = PackageLoader(t.cast(str, sys.modules[__name__].__package__))
    jinja_env = Environment(loader=template_loader, autoescape=select_autoescape(['html', 'xml']))
    template = jinja_env.get_template('project.cws.yml')
    output = project_conf
    with output.open("w") as f:
        f.write(template.render({'version': __version__.replace('.', '_')}))

    click.echo('New project created.')
