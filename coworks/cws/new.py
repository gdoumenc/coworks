import click
from pathlib import Path
from shutil import copyfile


@click.command("new", short_help="Creates a new CoWorks project.")
@click.option('--force', is_flag=True, help="Force creation even if already created.")
@click.pass_context
def new_command(ctx, force) -> None:
    debug = ctx.parent.params['debug']
    project_dir = Path(ctx.parent.params['project_dir'])
    project_templates = Path(__file__).parent / 'project_templates'

    if not project_dir.exists():
        if debug:
            click.echo(f"Ceate project directory {project_dir}.")
        project_dir.mkdir()

    # Copy project configuration file
    src = project_templates / 'project.cws.yml'
    dest = project_dir / 'project.cws.yml'

    if dest.exists() and not force:
        click.echo("Project already created. Set 'force' option for recreation.")
        return

    copyfile(src, dest)

    # Copy main app service
    src = project_templates / 'app.py'
    dest = project_dir / 'app.py'

    copyfile(src, dest)

    if debug:
        click.echo('New project created.')
