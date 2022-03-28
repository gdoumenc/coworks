import inspect
import sys
from inspect import Parameter

import markdown
from coworks import Blueprint
from coworks import entry
from coworks.globals import aws_event
from flask import current_app
from jinja2 import Environment
from jinja2 import PackageLoader
from jinja2 import select_autoescape


class Admin(Blueprint):
    """Administration blueprint to get details on the microservice containing it.
    """

    def __init__(self, name: str = 'admin', **kwargs):
        super().__init__(name=name, **kwargs)

    @entry(no_auth=True, no_cors=True, content_type='text/html; charset=utf-8')
    def get(self):
        """Returns the markdown documentation associated to this microservice.
        """
        md = getattr(current_app, 'doc_md', None)
        if not md:
            md = getattr(current_app.__class__, 'DOC_MD', None)
        if md:
            return markdown.markdown(md, extensions=['fenced_code'])

        if current_app.__class__.__doc__:
            return current_app.__class__.__doc__.replace('\n', ' ').strip(),

    @entry
    def get_route(self, prefix=None, blueprint=None):
        """Returns the list of entrypoints with signature.
        :param prefix: Prefix path to limit the number of returned routes.
        :param blueprint: Show named blueprint routes if defined ('__all__' or blueprint name).
        """
        routes = {}

        for rule in current_app.url_map.iter_rules():

            # if returns only prefixed routes
            if prefix and not rule.rule.startswith(prefix):
                continue

            route = {}
            function_called = current_app.view_functions[rule.endpoint]

            # Keeps app entries and  blueprint entries
            from_blueprint = getattr(function_called, '__CWS_FROM_BLUEPRINT')
            if from_blueprint is None or blueprint == '__all__' or from_blueprint == blueprint:
                for http_method in rule.methods:
                    if http_method not in ['HEAD', 'OPTIONS']:
                        doc = inspect.getdoc(function_called)
                        route[http_method] = {
                            'signature': get_signature(function_called),
                        }
                        if doc:
                            docstring = doc.replace('\n', ' ').split(':param ')
                            self.strip = docstring[0].strip()
                            route[http_method]['doc'] = self.strip
                            if len(docstring) > 1:
                                route[http_method]['params'] = docstring[1:]
                        if from_blueprint:
                            route[http_method]['blueprint'] = from_blueprint

                        route[http_method]['binary'] = getattr(function_called, '__CWS_BINARY')
                        route[http_method]['no_auth'] = getattr(function_called, '__CWS_NO_AUTH')
                        route[http_method]['no_cors'] = getattr(function_called, '__CWS_NO_CORS')
                        content_type = getattr(function_called, '__CWS_CONTENT_TYPE')
                        if content_type:
                            route[http_method]['content_type'] = content_type
                routes[rule.rule] = route

        return routes

    @entry
    def get_event(self):
        """Returns the calling event."""
        # noinspection PyProtectedMember
        return aws_event._get_current_object()

    def get_proxy(self):
        """Returns the calling context."""
        env = Environment(
            loader=PackageLoader(sys.modules[__name__].__name__),
            autoescape=select_autoescape(['html', 'xml']))
        env.filters["signature"] = inspect.signature
        env.filters["positional_params"] = positional_params
        env.filters["keyword_params"] = keyword_params

        data = {
            'name': current_app.name,
            'entries': current_app.url_map,
        }
        template = env.get_template("proxy.j2")
        return template.render(**data)


def get_signature(func):
    sig = ""
    params = inspect.signature(func).parameters
    for i, (k, p) in enumerate(params.items()):
        if i == 0:
            continue
        sp = k
        if p.annotation != Parameter.empty:
            sp = f"{sp}:{str(p.annotation)}"
        if p.default != Parameter.empty:
            sp = f"{sp}={p.default}"
        sig = f"{sp}" if i == 1 else f"{sig}, {sp}"
    return f"({sig})"


def positional_params(func):
    res = ''
    params = inspect.signature(func).parameters
    for i, (k, p) in enumerate(params.items()):
        if i == 0 or p.kind not in [Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD,
                                    Parameter.VAR_POSITIONAL]:
            continue
        if p.kind == Parameter.POSITIONAL_OR_KEYWORD and p.default != Parameter.empty:
            continue
        sp = f"'{k}' : {k}"
        res = f"{sp}" if i == 1 else f"{res}, {sp}"
    return res


def keyword_params(func):
    res = ''
    params = inspect.signature(func).parameters
    for i, (k, p) in enumerate(params.items()):
        if i == 0 or p.kind not in [Parameter.KEYWORD_ONLY, Parameter.POSITIONAL_OR_KEYWORD, Parameter.VAR_KEYWORD]:
            continue
        if p.kind == Parameter.POSITIONAL_OR_KEYWORD and p.default == Parameter.empty:
            continue
        sp = f"'{k}' : {k}"
        res = f"{sp}" if i == 1 else f"{res}, {sp}"
    return res
