import os
import shutil
import sys

import click
from coworks.version import __version__

from chalice.cli import CONFIG_VERSION, DEFAULT_STAGE_NAME, DEFAULT_APIGATEWAY_STAGE_NAME
from chalice.cli import chalice_version, get_system_info
from chalice.utils import serialize_to_json
from .factory import CWSFactory


@click.group()
@click.version_option(version=__version__,
                      message=f'%(prog)s %(version)s, chalice {chalice_version}, {get_system_info()}')
@click.option('--project-dir',
              help='The project directory path (absolute or relative).'
                   'Defaults to CWD')
@click.pass_context
def client(ctx, project_dir=None):
    if project_dir is None:
        project_dir = os.getcwd()
    elif not os.path.isabs(project_dir):
        project_dir = os.path.abspath(project_dir)
    ctx.obj['project_dir'] = project_dir


@client.command('init')
@click.option('--force/--no-force', default=False,
              help='Forces project reinitialization.')
@click.pass_context
def init(ctx, force):
    project_name = os.path.basename(os.path.normpath(os.getcwd()))

    chalice_dir = os.path.join('.chalice')
    if os.path.exists(chalice_dir):
        if force:
            shutil.rmtree(chalice_dir)
            created = False
        else:
            sys.stderr.write(f"Project {project_name} already initialized\n")
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
        sys.stdout.write(f"Project {project_name} initialized\n")
    else:
        sys.stdout.write(f"Project {project_name} reinitialized\n")


@client.command('run')
@click.option('-m', '--module', default='app')
@click.option('-a', '--app', default='app')
@click.option('-h', '--host', default='127.0.0.1')
@click.option('-p', '--port', default=8000, type=click.INT)
@click.option('-s', '--stage', default=DEFAULT_STAGE_NAME, type=click.STRING,
              help='Name of the Chalice stage for the local server to use.')
@click.option('--debug/--no-debug', default=False,
              help='Print debug logs to stderr.')
@click.pass_context
def run(ctx, module, app, host, port, stage, debug):
    handler = CWSFactory.import_attr(module, app, project_dir=ctx.obj['project_dir'])
    handler.run(host=host, port=port, stage=stage, debug=debug, project_dir=ctx.obj['project_dir'])


@client.command('export')
@click.option('-m', '--module', default='app')
@click.option('-a', '--app', default='app')
@click.option('-f', '--format', default='list')
@click.option('-o', '--out')
@click.pass_context
def export(ctx, module, app, format, out):
    project_dir = ctx.obj['project_dir']
    handler = CWSFactory.import_attr(module, app, project_dir=project_dir)
    try:
        writer = handler.extensions['writers'][format]
    except KeyError:
        sys.stderr.write(f"Format '{format}' undefined\n")
        return

    return writer.export(out, module_name=module, handler_name=app)


def main():
    return client(obj={})
