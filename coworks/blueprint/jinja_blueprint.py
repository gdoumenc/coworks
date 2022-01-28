import typing as t

from flask.globals import current_app
from jinja2 import Template
from werkzeug.datastructures import FileStorage

from coworks import Blueprint
from coworks import entry


class Jinja(Blueprint):

    def __init__(self, name: str = "jinja", autoescape: bool = True, **kwargs):
        super().__init__(name=name, **kwargs)
        self.autoescape = autoescape

    @entry(content_type='text/html; charset=utf-8')
    def post_render(self, template="", **context):
        """Returns the templating result."""
        if type(template) == FileStorage:
            template = t.cast(FileStorage, template).stream.read().decode()
        template = Template(template, autoescape=self.autoescape)
        current_app.update_template_context(context)
        return template.render(config=current_app.config, **context)
