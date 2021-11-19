import click


class ExitCommand(click.exceptions.Exit):
    def __init__(self, msg):
        super().__init__()
        self.msg = msg
