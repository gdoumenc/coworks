import typing as t
from contextlib import contextmanager
from threading import Thread
from time import sleep

import click


class ProgressBar:

    def __init__(self, bar):
        self.bar = bar
        self.stop = False
        self.spin_thread = None

    def echo(self, msg):
        swap = self.bar.format_progress_line
        self.bar.format_progress_line = lambda: msg
        self.bar.render_progress()
        click.echo()
        self.bar.format_progress_line = swap

    def update(self, msg: str = None):
        if msg:
            self.echo(msg)
        self.bar.update(1)

    def terminate(self, msg=None):
        self.stop = True
        if self.spin_thread:
            self.spin_thread.join()
        self.bar.finish()
        self.bar.render_progress()
        if msg:
            self.echo(msg)


class DebugProgressBar():

    def echo(self, msg):
        if msg:
            click.echo("==> " + msg)

    def update(self, msg=None):
        self.echo(msg)

    def terminate(self, msg=None):
        self.echo(msg)


@contextmanager
def progressbar(length=200, *, threaded=False, label: str = None) -> t.ContextManager[ProgressBar]:
    """Spinner progress bar.
    Creates it with a task label and updates it with progress messages using the 'update' function.
    """
    if threaded:
        try:
            with click.progressbar(range(length - 1), label=label.ljust(40), show_eta=False) as bar:
                pb = ProgressBar(bar)

                def display_spinning_cursor():
                    while not pb.stop:
                        sleep(1)
                        if not pb.stop:
                            pb.update()

                spin_thread = Thread(target=display_spinning_cursor)
                spin_thread.start()
                pb.spin_thread = spin_thread
                yield pb
                if not pb.stop:
                    pb.terminate()
        except (Exception,) as e:
            click.echo(f"{type(e).__name__}: {str(e)}")
        finally:
            pb.stop = True
    else:
        yield DebugProgressBar()
