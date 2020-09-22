from .command import CwsCommand
import click


class CwsInfo(CwsCommand):
    def __init__(self, app=None, name='info'):
        super().__init__(app, name=name)

    @property
    def options(self):
        return [
            *super().options,
            click.option('--full/--no-full', default=False, help='Print complete description.')
        ]

    def _execute(self, project_dir, module, service, full, **options):
        if not full:
            print(f"microservice {service} defined in {project_dir}/{module}.py")
        else:
            print(f"microservice {service}:")
            print(f"\tdefined in folder {project_dir}")
            print(f"\tdefined in module {module}.py")
            print(f"\tnummber of entries {len(self.app.routes.keys())}")
            print(f"\troutes {[r for r in self.app.routes.keys()]}")