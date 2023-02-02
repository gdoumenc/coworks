from click import Command
from click import UsageError

def no_project_context(f):
    setattr(f, '__need_project_context', False)
    return f

class CwsCommand(Command):

    def invoke(self, ctx):
        if getattr(self.callback, '__need_project_context', True) and self._context_project_dir(ctx):
            raise UsageError(f"Project dir {self._context_project_dir(ctx)} not found.")
        return super().invoke(ctx)

    @staticmethod
    def _context_project_dir(ctx):
        if ctx.parent is None:
            return ctx.params.get('project_dir')
        return CwsCommand._context_project_dir(ctx.parent)
