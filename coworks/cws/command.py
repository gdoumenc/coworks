import sys
from abc import ABC, abstractmethod

import click

from coworks import TechMicroService
from coworks.cws.error import CwsCommandError


class CwsCommand(click.Command, ABC):

    @classmethod
    def multi_execute(cls, project_dir, workspace, execution_params):
        for command, options in execution_params:
            command.execute(**options)

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

            for opt in self.app.commands[cmd].options:
                opt(self)

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
