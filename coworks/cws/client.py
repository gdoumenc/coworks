import os
import sys
from functools import partial

import click
from chalice.cli import chalice_version, get_system_info

from coworks.version import __version__
from coworks.utils import import_attr


class CLIError(Exception):
    ...


def check_handler(ctx):
    project_dir = ctx.params.get('project_dir')
    if project_dir is None:
        project_dir = os.getcwd()
    elif not os.path.isabs(project_dir):
        project_dir = os.path.abspath(project_dir)
    module = ctx.params.get('module')
    service = ctx.params.get('service')

    # Load handler
    try:
        ctx.obj['handler'] = handler = import_attr(module, service, cwd=project_dir)
    except AttributeError as e:
        sys.stderr.write(f"Module '{module}' has no microservice {service} : {str(e)}\n")
        raise CLIError()
    except ModuleNotFoundError as e:
        sys.stderr.write(f"The module '{module}' is not defined in {project_dir} : {str(e)}\n")
        raise CLIError()
    except Exception as e:
        sys.stderr.write(f"Error {e} when loading module '{module}'\n")
        raise CLIError()

    # Set other parameters
    ctx.obj['project_dir'] = project_dir
    ctx.obj['module'] = module
    ctx.obj['service'] = service

    # Adds commands from handler
    for name, cmd in handler.commands.items():
        if name not in ctx.protected_args:
            continue

        def execute(ctx, **kwargs):
            try:
                command = ctx.obj['handler'].commands[name]
                command.execute(**ctx.obj, **kwargs)
            except CLIError:
                sys.exit(1)
            except Exception as e:
                sys.stderr.write(str(e))
                sys.exit(1)

        f = click.pass_context(execute)
        for opt in cmd.options:
            f = opt(f)
        return client.command(name)(f)


@click.group()
@click.version_option(version=__version__,
                      message=f'%(prog)s %(version)s, chalice {chalice_version}, {get_system_info()}')
@click.option('-p', '--project-dir', default=None,
              help='The project directory path (absolute or relative). Defaults to CWD')
@click.option('-m', '--module', default='app', help="Filename of your microservice python source file.")
@click.option('-s', '--service', default='app', help="Coworks application in the source file.")
@click.pass_context
def client(*args, **kwargs):
    ...


def invoke(initial, ctx):
    try:
        check_handler(ctx)
    except CLIError:
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(str(e))
        sys.exit(1)
    initial(ctx)


client.invoke = partial(invoke, client.invoke)


def main():
    return client(obj={})


if __name__ == "__main__":
    main()
