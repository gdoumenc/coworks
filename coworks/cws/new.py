import click
from distutils.dir_util import copy_tree
from pathlib import Path

from .utils import progressbar


@click.command("new", short_help="Creates a new CoWorks project.")
@click.option('--force', is_flag=True, help="Force creation even if already created.")
@click.pass_context
def new_command(ctx, force) -> None:
    debug = ctx.parent.params['debug']
    project_dir = Path(ctx.parent.params['project_dir'])
    project_templates = Path(__file__).parent / 'project_templates'

    with progressbar(3, label='Creating new project') as bar:

        # Creates folder
        if not project_dir.exists():
            if debug:
                bar.echo(f"Create project directory {project_dir}.")
            project_dir.mkdir()
        bar.update()

        # Copy project configuration file
        src = project_templates
        dest = project_dir

        if dest.exists() and not force:
            bar.terminate("Project already created. Set 'force' option for recreation.")
            return

        copy_tree(src.as_posix(), dest.as_posix())
        bar.update()

        if debug:
            bar.terminate('New project created.')
