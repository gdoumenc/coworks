import sys
from abc import ABC, abstractmethod


class CwsCommand(ABC):

    def __init__(self, app=None, *, name):
        self.name = name

        # Trace interfaces.
        self.output = sys.stdout
        self.error = sys.stderr

        # A list of functions that will be called before or after the command executioon.
        self.before_funcs = []
        self.after_funcs = []

        if app is not None:
            self.app = app
            self.init_app(app)

    def init_app(self, app):
        app.commands[self.name] = self

    @property
    def options(self):
        return ()

    def execute(self, output=None, error=None, **kwargs):
        """ Called when the command is called.
        :param output: output stream.
        :param error: error stream.
        :param kwargs: environment parameters for the command.
        :return: None
        """
        if output is not None:
            self.output = open(output, 'w+') if type(output) is str else output
        if error is not None:
            self.error = open(error, 'w+') if type(error) is str else error

        for func in self.before_funcs:
            func(**kwargs)

        self._execute(**kwargs)

        for func in self.after_funcs:
            func(**kwargs)

    def before_execute(self, f):
        """Registers a function to be run before the command execution.
        :param f: function called before the command execution
        :return: None

        May be used as a decorator.

        The function will be called without any arguments and its return value is ignored.
        """

        self.after_funcs.append(f)
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

    def _export_header(self, **kwargs):
        ...

    @abstractmethod
    def _execute(self, **kwargs):
        """ Main command function.
        :param kwargs: Environment parameters for export.
        :return: None.

        Abstract method which must be redefined in any subclass. The content should be written in self.output.
        """
