import json
import os
import sys
import traceback
from tempfile import SpooledTemporaryFile

import click
from chalice import BadRequestError
from chalice.cli import chalice_version, get_system_info

from coworks import BizFactory
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


@client.command('info')
@click.option('-m', '--module', default='app',
              help="Filename of your microservice python source file.")
@click.option('-s', '--service', default='app',
              help="Coworks application in the source file.")
@click.option('-o', '--out')
@click.pass_context
def info(ctx, module, service, out):
    """Information on a microservice."""
    try:
        handler = import_attr(module, service, cwd=ctx.obj['project_dir'])
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
@click.option('-s', '--service', default='app',
              help="Coworks application in the source file.")
@click.option('-h', '--host', default='127.0.0.1')
@click.option('-p', '--port', default=8000, type=click.INT)
@click.option('--debug/--no-debug', default=False,
              help='Print debug logs to stderr.')
@click.pass_context
def run(ctx, module, service, host, port, debug):
    """Run local server."""
    try:
        handler = import_attr(module, service, cwd=ctx.obj['project_dir'])
        handler.run(host=host, port=port, debug=debug, project_dir=ctx.obj['project_dir'])
    except CLIError:
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e))
        sys.exit(1)


@client.command('export')
@click.option('-m', '--module', default='app',
              help="Filename of your microservice python source file.")
@click.option('-s', '--service', default='app',
              help="Coworks application in the source file.")
@click.option('-b', '--biz', default=None,
              help="BizMicroservice name.")
@click.option('-f', '--format', default='terraform')
@click.option('-o', '--out')
@click.option('-v', '--variables', type=(str, str), multiple=True, help="Additionnal variables")
@click.option('--debug/--no-debug', default=False,
              help='Print debug logs to stderr.')
@click.pass_context
def export(ctx, module, service, biz, format, out, variables, debug):
    """Export microservice in other description languages."""
    try:
        export_to_file(module, service, format, out, project_dir=ctx.obj['project_dir'], biz=biz, variables=dict(variables))
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
@click.option('-s', '--service', default='app',
              help="Coworks application in the source file.")
@click.option('-p', '--profile', default=None)
@click.pass_context
def update(ctx, module, service, profile):
    """Update biz microservice."""
    out = SpooledTemporaryFile(mode='w+')
    handler = export_to_file(module, service, 'sfn', out, project_dir=ctx.obj['project_dir'])
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


def import_attr(module, service, cwd):
    try:
        return CwsCLIFactory.import_attr(module, service, cwd=cwd)
    except AttributeError as e:
        sys.stderr.write(f"Module '{module}' has no microservice {service} : {str(e)}\n")
        raise CLIError()
    except ModuleNotFoundError as e:
        sys.stderr.write(f"They module '{module}' is not defined in {cwd} : {str(e)}\n")
        raise CLIError()
    except Exception as e:
        sys.stderr.write(f"Error {e} when loading module '{module}'\n")
        raise CLIError()


def export_to_file(module, service, _format, out, **kwargs):
    handler = import_attr(module, service, cwd=kwargs['project_dir'])
    try:
        _writer: Writer = handler.extensions['writers'][_format]
    except KeyError as e:
        sys.stderr.write(f"Format '{_format}' undefined (you haven't add a {_format} writer to {service} )\n")
        raise CLIError()

    _writer.export(output=out, module_name=module, handler_name=service, **kwargs)


def update_sfn(handler, src):
    sfn_client = handler.sfn_client
    response = sfn_client.update_state_machine(stateMachineArn=handler.sfn_arn, definition=src)
    print(response)


def main():
    return client(obj={})
