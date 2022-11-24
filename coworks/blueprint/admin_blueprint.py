import inspect
import sys
from collections import defaultdict
from inspect import Parameter

import markdown
from flask import current_app
from flask import render_template_string
from jinja2 import Environment
from jinja2 import PackageLoader
from jinja2 import select_autoescape
from werkzeug.exceptions import NotFound

from coworks import Blueprint
from coworks import entry


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

        top = ""
        if md:
            top = markdown.markdown(md, extensions=['fenced_code'])
        if current_app.__class__.__doc__:
            top = current_app.__class__.__doc__.replace('\n', ' ').strip()
            
        header = '<img src="https://neorezo.io/assets/img/logo_neorezo.png" width="100" />'

        template = """<style type="text/css">ul.nobull {list-style-type: none;}</style>
        <ul class="nobull">{% for entry,route in routes.items() %}
        <li>{{ entry }} : <ul>{% for method,info in route.items() %}
        <li>{{ method }}{{ info.signature }} : <i>{{ info.doc }}</i>{% endfor %}</li>
        </ul></li>{% endfor %}</ul>"""
        routes = dict(sorted(self.get_route(blueprint="__all__").items()))
        bottom = render_template_string(template, routes=routes)

        return header + '<hr/>' + top + '<hr/>' + bottom

    @entry
    def get_route(self, prefix=None, blueprint=None):
        """Returns the list of entrypoints with signature.

        :param prefix: Prefix path to limit the number of returned routes.
        :param blueprint: Show named blueprint routes if defined ('__all__' or blueprint name).
        """
        if blueprint and (blueprint != '__all__' and blueprint not in current_app.blueprints):
            raise NotFound(f"Undefined blueprint {blueprint}")

        routes = defaultdict(dict)

        for rule in current_app.url_map.iter_rules():

            # Must return only prefixed routes
            if prefix:
                if rule.rule.startswith(prefix):
                    self.add_route_from_rule(routes, rule)
                else:
                    continue

            function_called = current_app.view_functions[rule.endpoint]
            from_blueprint = getattr(function_called, '__CWS_FROM_BLUEPRINT')

            # Must return only blueprint routes
            if blueprint:
                if blueprint == '__all__' or from_blueprint == blueprint:
                    self.add_route_from_rule(routes, rule)
                else:
                    continue

            if from_blueprint is None:
                self.add_route_from_rule(routes, rule)

        return routes

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

    def add_route_from_rule(self, routes, rule):
        route = {}
        for http_method in rule.methods:
            if http_method not in ['HEAD', 'OPTIONS']:
                function_called = current_app.view_functions[rule.endpoint]
                route[http_method] = {
                    'signature': get_signature(function_called),
                    'endpoint': rule.endpoint,
                    'binary': getattr(function_called, '__CWS_BINARY'),
                    'no_auth': getattr(function_called, '__CWS_NO_AUTH'),
                    'no_cors': getattr(function_called, '__CWS_NO_CORS'),
                }

                from_blueprint = getattr(function_called, '__CWS_FROM_BLUEPRINT')
                if from_blueprint:
                    route[http_method]['blueprint'] = from_blueprint

                content_type = getattr(function_called, '__CWS_CONTENT_TYPE')
                if content_type:
                    route[http_method]['content_type'] = content_type

                doc = inspect.getdoc(function_called)
                if doc:
                    docstring = doc.replace('\n', ' ').split(':param ')
                    route[http_method]['doc'] = docstring[0].strip()
                    if len(docstring) > 1:
                        # noinspection PyTypeChecker
                        route[http_method]['params'] = docstring[1:]

        routes[rule.rule].update(route)


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
