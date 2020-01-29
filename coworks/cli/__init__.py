import os
import shutil

import click
from chalice.cli import CONFIG_VERSION, DEFAULT_STAGE_NAME, DEFAULT_APIGATEWAY_STAGE_NAME
from chalice.cli import main as chalice_main, cli as chalice_cli, chalice_version, get_system_info
from chalice.utils import UI, serialize_to_json

from coworks.version import __version__

click.version_option(version=__version__,
                     message=f'%(prog)s %(version)s, chalice {chalice_version}, {get_system_info()}')(chalice_cli)


@chalice_cli.command('init')
@click.option('--force/--no-force')
@click.pass_context
def init(ctx, force):
    ui = UI()
    project_name = os.path.basename(os.path.normpath(os.getcwd()))

    chalice_dir = os.path.join('.chalice')
    if os.path.exists(chalice_dir):
        if force:
            shutil.rmtree(chalice_dir)
            created = False
        else:
            ui.write(f"Project {project_name} already initialized\n")
            return
    else:
        created = True

    os.makedirs(chalice_dir)
    config = os.path.join('.chalice', 'config.json')
    cfg = {
        'version': CONFIG_VERSION,
        'app_name': project_name,
        'stages': {
            DEFAULT_STAGE_NAME: {
                'api_gateway_stage': DEFAULT_APIGATEWAY_STAGE_NAME,
            }
        }
    }
    with open(config, 'w') as f:
        f.write(serialize_to_json(cfg))

    if created:
        ui.write(f"Project {project_name} initialized\n")
    else:
        ui.write(f"Project {project_name} reinitialized\n")


main = chalice_main
