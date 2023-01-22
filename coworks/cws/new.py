import sys
from distutils.dir_util import copy_tree
from pathlib import Path

import click
from jinja2 import Environment
from jinja2 import PackageLoader
from jinja2 import select_autoescape

from coworks.version import __version__
from .command import CwsCommand
from .command import no_project_context


@click.command("new", CwsCommand, short_help="Creates a new CoWorks project.")
@click.option('--force', is_flag=True, help="Force creation even if already created.")
@no_project_context
def new_command(force) -> None:
    project_templates = Path(__file__).parent / 'project_templates'

    # Copy project configuration file
    src = project_templates
    project_conf = Path("project.cws.yml")

    if project_conf.exists() and not force:
        click.echo("Project already created. Set 'force' option for recreation.")
        return

    # Copy files
    copy_tree(src.as_posix(), '.')
    Path('template.env').rename('.env')

    # Render project configuration file
    template_loader = PackageLoader(sys.modules[__name__].__package__)
    jinja_env = Environment(loader=template_loader, autoescape=select_autoescape(['html', 'xml']))
    template = jinja_env.get_template('project.cws.yml')
    output = project_conf
    with output.open("w") as f:
        f.write(template.render({'version': __version__.replace('.', '_')}))

    click.echo('New project created.')
