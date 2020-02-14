from coworks import Writer as CWSWriter

class Writer(CWSWriter):

    def export(self, app, output=None):
        return self.write("my writer", output)
