import json
import os
import shutil
import sys
import traceback
from tempfile import SpooledTemporaryFile

import click
from chalice import BadRequestError
from chalice.cli import CONFIG_VERSION, DEFAULT_STAGE_NAME, DEFAULT_APIGATEWAY_STAGE_NAME
from chalice.cli import chalice_version, get_system_info
from chalice.local import LocalChalice
from chalice.utils import serialize_to_json
from coworks import TechMicroService, BizMicroService, BizFactory
from coworks.cws.writer import Writer
from coworks.version import __version__

from .factory import CwsCLIFactory


class CLIError(Exception):
    ...


@click.group()
@click.version_option(version=__version__,
                      message=f'%(prog)s %(version)s, chalice {chalice_version}, {get_system_info()}')
@click.option('-p', '--project-dir',
              help='The project directory path (absolute or relative). Defaults to CWD')
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
    """Init chalice configuration file."""
    project_name = os.path.basename(os.path.normpath(ctx.obj['project_dir']))

    chalice_dir = os.path.join(ctx.obj['project_dir'], '.chalice')
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
    config = os.path.join(chalice_dir, 'config.json')
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


@client.command('info')
@click.option('-m', '--module', default='app',
              help="Filename of your microservice python source file.")
@click.option('-a', '--app', default='app',
              help="Coworks application in the source file.")
@click.option('-o', '--out')
@click.pass_context
def info(ctx, module, app, out):
    """Information on a microservice."""
    try:
        handler = import_attr(module, app, cwd=ctx.obj['project_dir'])
        if out is not None:
            soutput = open(out, 'w+') if type(out) is str else out
        else:
            out = sys.stdout
        print(json.dumps({
            'name': handler.app_name,
            'type': handler.ms_type
        }), file=out)
    except CLIError:
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e))
        sys.exit(1)


@client.command('run')
@click.option('-m', '--module', default='app',
              help="Filename of your microservice python source file.")
@click.option('-a', '--app', default='app',
              help="Coworks application in the source file.")
@click.option('-h', '--host', default='127.0.0.1')
@click.option('-p', '--port', default=8000, type=click.INT)
@click.option('-s', '--stage', default='dev')
@click.option('--debug/--no-debug', default=False,
              help='Print debug logs to stderr.')
@click.pass_context
def run(ctx, module, app, host, port, stage, debug):
    """Run local server."""
    try:
        handler = import_attr(module, app, cwd=ctx.obj['project_dir'])
        handler.run(host=host, port=port, stage=stage, debug=debug, project_dir=ctx.obj['project_dir'])
    except CLIError:
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e))
        sys.exit(1)


@client.command('export')
@click.option('-m', '--module', default='app',
              help="Filename of your microservice python source file.")
@click.option('-a', '--app', default='app',
              help="Coworks application in the source file.")
@click.option('-b', '--biz', default=None,
              help="BizMicroservice name.")
@click.option('-f', '--format', default='terraform')
@click.option('-o', '--out')
@click.option('--debug/--no-debug', default=False,
              help='Print debug logs to stderr.')
@click.pass_context
def export(ctx, module, app, biz, format, out, debug):
    """Export microservice in other description languages."""
    try:
        export_to_file(module, app, format, out, project_dir=ctx.obj['project_dir'], biz=biz)
    except CLIError:
        sys.exit(1)
    except Exception as e:
        if debug:
            traceback.print_exc()
        sys.stderr.write(str(e))
        sys.exit(1)


@client.command('update')
@click.option('-m', '--module', default='app',
              help="Filename of your microservice python source file.")
@click.option('-a', '--app', default='app',
              help="Coworks application in the source file.")
@click.option('-p', '--profile', default=None)
@click.pass_context
def update(ctx, module, app, profile):
    """Update biz microservice."""
    out = SpooledTemporaryFile(mode='w+')
    handler = export_to_file(module, app, 'sfn', out, project_dir=ctx.obj['project_dir'])
    if handler is None:
        sys.exit(1)
    handler.aws_profile = profile

    out.seek(0)
    if isinstance(handler, BizFactory):
        try:
            update_sfn(handler, out.read())
        except BadRequestError:
            sys.stderr.write(f"Cannot update undefined step function '{handler.sfn_name}'.\n")
            sys.exit(1)

    else:
        sys.stderr.write(f"Update not defined on {type(handler)}.\n")
        sys.exit(1)


def import_attr(module, app, cwd):
    try:
        return CwsCLIFactory.import_attr(module, app, cwd=cwd)
    except AttributeError:
        sys.stderr.write(f"Module '{module}' has no microservice {app} : {str(e)}\n")
        raise CLIError()
    except ModuleNotFoundError as e:
        sys.stderr.write(f"They module '{module}' is not defined in {cwd} : {str(e)}\n")
        raise CLIError()
    except Exception as e:
        sys.stderr.write(f"Error {e} when loading module '{module}'\n")
        raise CLIError()


def export_to_file(module, app, _format, out, **kwargs):
    handler = import_attr(module, app, cwd=kwargs['project_dir'])

    try:
        _writer: Writer = handler.extensions['writers'][_format]
    except KeyError as e:
        sys.stderr.write(f"Format '{_format}' undefined (you haven't add a {_format} writer to {app} )\n")
        raise CLIError()

    _writer.export(output=out, module_name=module, handler_name=app, **kwargs)


def update_sfn(handler, src):
    sfn_client = handler.sfn_client
    response = sfn_client.update_state_machine(stateMachineArn=handler.sfn_arn, definition=src)
    print(response)


def main():
    return client(obj={})
