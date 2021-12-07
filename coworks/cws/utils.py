import click
import typing as t
from contextlib import contextmanager
from threading import Thread
from time import sleep


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

    def update(self, n_steps: int = 1, *, msg: str = None):
        if msg:
            self.echo(msg)
        self.bar.update(n_steps)

    def terminate(self, msg=None):
        self.stop = True
        if self.spin_thread:
            self.spin_thread.join()
        self.bar.finish()
        self.bar.render_progress()
        if msg:
            self.echo(msg)


@contextmanager
def progressbar(length=200, *, threaded=False, label: str = None) -> t.ContextManager[ProgressBar]:
    with click.progressbar(range(length - 1), label=label, show_eta=False) as bar:
        pg = ProgressBar(bar)
        if threaded:

            def display_spinning_cursor():
                while not pg.stop:
                    sleep(1)
                    pg.update()

            spin_thread = Thread(target=display_spinning_cursor)
            spin_thread.start()
            pg.spin_thread = spin_thread
        yield pg
        if not pg.stop:
            pg.terminate()
