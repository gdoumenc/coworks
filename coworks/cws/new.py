from pathlib import Path
from shutil import copyfile

import click

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
        src = project_templates / 'project.cws.yml'
        dest = project_dir / 'project.cws.yml'

        if dest.exists() and not force:
            bar.terminate("Project already created. Set 'force' option for recreation.")
            return

        copyfile(src, dest)
        bar.update()

        # Copy main app service
        src = project_templates / 'app.py'
        dest = project_dir / 'app.py'

        copyfile(src, dest)
        bar.update()

        if debug:
            bar.terminate('New project created.')
