import sys
from abc import ABC, abstractmethod
from collections import defaultdict

import click

from .error import CwsCommandError
from ..coworks import TechMicroService


class CwsClientCommandOptions:

    def __init__(self, client_options, execution_context):
        self.client_options = client_options
        self.execution_context = execution_context

    def get(self, option, default_value=None):
        return self.client_options.get(option, default_value)

    def pop(self, option, default_value):
        """Removes from client option and all command options."""
        value = self.client_options.pop(option, default_value)
        for execution_params in self.execution_context.values():
            for command, command_options in execution_params:
                command_options.pop(option, None)
        return value


class CwsMultiCommands:
    def __init__(self):
        self.client_options = None
        self.execution_context = defaultdict(list)

    def append(self, client_options, command, command_options):
        if self.client_options is None:
            self.client_options = CwsClientCommandOptions(client_options, self.execution_context)
        self.execution_context[type(command)].append((command, command_options))

    def items(self):
        for command_class, execution_params in self.execution_context.items():
            yield command_class, execution_params


class CwsCommand(click.Command, ABC):

    @classmethod
    def multi_execute(cls, project_dir, workspace, client_options, execution_context):
        for command, command_options in execution_context:
            command.execute(**command_options)

    def __init__(self, app: TechMicroService = None, *, name):
        super().__init__(name, callback=self._execute)

        # Trace interfaces.
        self.output = sys.stdout
        self.error = sys.stderr

        # A list of functions that will be called before or after the command executioon.
        self.before_funcs = []
        self.after_funcs = []

        if app is not None:
            self.app = app
            self.init_app(app)

        for opt in self.options:
            opt(self)

    def init_app(self, app):
        app.commands[self.name] = self
        for cmd in self.needed_commands:
            if cmd not in app.commands:
                raise CwsCommandError(f"Undefined command {cmd} needed.")

    @property
    def needed_commands(self):
        return []

    @property
    def options(self):
        return []

    def execute(self, *, project_dir, module, service, workspace, output=None, error=None, **options):
        """ Called when the command is called.
        :param output: output stream.
        :param error: error stream.
        :param options: command options.
        :return: None
        """
        self.app.deferred_init(workspace)

        if output is not None:
            self.output = open(output, 'w+') if type(output) is str else output
        if error is not None:
            self.error = open(error, 'w+') if type(error) is str else error

        try:
            for func in self.before_funcs:
                func(options)

            ctx = self.make_context(self.name, options)
            ctx_options = {**options, 'output': output, 'error': error}
            ctx.params.update(project_dir=project_dir, module=module, service=service, workspace=workspace,
                              **ctx_options)
            self.invoke(ctx)

            for func in self.after_funcs:
                func(options)
        except click.exceptions.Exit as e:
            if e.exit_code:
                raise CwsCommandError("Command exits with error")
            return
        except CwsCommandError:
            raise
        except Exception as e:
            raise CwsCommandError(str(e))

    def before_execute(self, f):
        """Registers a function to be run before the command execution.
        :param f: function called before the command execution
        :return: None

        May be used as a decorator.

        The function will be called without any arguments and its return value is ignored.
        """

        self.before_funcs.append(f)
        return f

    def after_execute(self, f):
        """Registers a function to be run after the command execution.
        :param f: function called after the command execution
        :return: None

        May be used as a decorator.

        The function will be called without any arguments and its return value is ignored.
        """

        self.after_funcs.append(f)
        return f

    def parse_args(self, ctx, args):
        for param in self.get_params(ctx):
            if param.name not in args:
                if param.required:
                    raise CwsCommandError(f"missing parameter: {param.name}")
                args[param.name] = param.get_default(ctx)
        ctx.args = args
        return args

    @abstractmethod
    def _execute(self, **options):
        """ Main command function.
        :param options: Command options.
        :return: None.

        Abstract method which must be redefined in any subclass. The content should be written in self.output.
        """
