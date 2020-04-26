import urllib.parse

import jinja2
from chalice import NotFoundError

from coworks import TechMicroService


class JinjaRenderMicroService(TechMicroService):
    """ Render a jinja template to html
        Templates can be sent to the microservice in 2 differents ways :
            - send files in multipart/form-data body
            - put template content in url """

    def __init__(self, globals=None, filters=None, **kwargs):
        super().__init__(**kwargs)
        self.globals = globals
        self.filters = filters

    def create_environment(self, loader):
        env = jinja2.Environment(loader=loader)
        if self.globals:
            env.globals.update(**self.globals)
        if self.filters:
            env.filters.update(**self.filters)
        return env

    def post_render(self, template_to_render_name, templates=None, context=None):
        """ render the template named template_to_render_name using templates sources given in templates
            pass templates as files of a multipart/form-data body
            pass context as a json file """
        if templates is None:
            raise NotFoundError("At least one template is expected")

        templates = [templates] if not isinstance(templates, list) else templates
        context = context if context is not None else {}
        templates_dict = {template.file.name: template.file.read().decode('utf-8') for template in templates}
        env = self.create_environment(loader=jinja2.DictLoader(templates_dict))
        template_to_render = env.get_template(template_to_render_name)
        render = template_to_render.render(**context)
        return {"render": render}

    def get_render_(self, template):
        """ render template which content is given in url
        pass jinja context in query_params """
        template = urllib.parse.unquote_plus(template)
        query_params = self.current_request.query_params
        context = {}
        for query_param in query_params:
            context[query_param] = query_params.getlist(query_param)
        env = self.create_environment(loader=jinja2.DictLoader({'index.html': template}))
        template = env.get_template('index.html')
        render = template.render(**context)
        return {"render": render}

