import sys
from distutils.dir_util import copy_tree
from pathlib import Path

import click
from jinja2 import Environment
from jinja2 import PackageLoader
from jinja2 import select_autoescape

from coworks.utils import get_app_debug
from coworks.version import __version__
from .utils import progressbar


@click.command("new", short_help="Creates a new CoWorks project.")
@click.option('--force', is_flag=True, help="Force creation even if already created.")
@click.pass_context
def new_command(ctx, force) -> None:
    debug = get_app_debug()
    project_dir = Path(ctx.parent.params['project_dir'])
    project_templates = Path(__file__).parent / 'project_templates'

    with progressbar(3, label='Creating new project') as bar:

        # Copy project configuration file
        src = project_templates
        dest = project_dir
        project_conf = project_dir / "project.cws.yml"

        if project_conf.exists() and not force:
            bar.terminate("Project already created. Set 'force' option for recreation.")
            return

        # Creates folder
        if not project_dir.exists():
            if debug:
                bar.echo(f"Create project directory {project_dir}.")
            project_dir.mkdir()
        bar.update()

        # Copy files
        copy_tree(src.as_posix(), dest.as_posix())
        bar.update()

        # Render project configuration file
        template_loader = PackageLoader(sys.modules[__name__].__package__)
        jinja_env = Environment(loader=template_loader, autoescape=select_autoescape(['html', 'xml']))
        template = jinja_env.get_template('project.cws.yml')
        output = dest / 'project.cws.yml'
        with output.open("w") as f:
            f.write(template.render({'version': __version__.replace('.', '_')}))
        bar.update()

        if debug:
            bar.terminate('New project created.')
