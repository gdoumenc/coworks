import platform
import sys
import typing as t
from contextlib import contextmanager
from importlib.metadata import version
from threading import Thread
from time import sleep

import click


def get_system_info():
    flask_version = version("flask")

    flask_info = f"flask {flask_version}"
    python_info = f"python {sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}"
    platform_system = platform.system().lower()
    platform_release = platform.release()
    platform_info = f"{platform_system} {platform_release}"
    return f"{flask_info}, {python_info}, {platform_info}"


def show_stage_banner(stage: str = 'dev'):
    click.secho(f" * Stage: {stage}", fg="green")


def show_terraform_banner(cloud: bool, refresh: bool):
    click.secho(f" * Using terraform backend {'cloud' if cloud else 's3'} (refresh={refresh})", fg="green")


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

    def update(self, msg: str | None = None):
        if msg:
            self.echo(msg)
        self.bar.update(1)

    def terminate(self, msg: str | None = None):
        self.stop = True
        if self.spin_thread:
            self.spin_thread.join()
        self.bar.finish()
        self.bar.render_progress()
        if msg:
            self.echo(msg)


class DebugProgressBar:

    def echo(self, msg: str):
        if msg:
            click.echo("==> " + msg)


@contextmanager  # type: ignore[arg-type]
def progressbar(length=200, *, label: str, threaded: bool = False) -> t.ContextManager[ProgressBar]:  # type: ignore
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
