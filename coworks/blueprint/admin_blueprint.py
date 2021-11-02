import inspect
import os
import sys
from inspect import Parameter

from flask import current_app
from flask import json
from jinja2 import Environment
from jinja2 import PackageLoader
from jinja2 import select_autoescape

from coworks import Blueprint
from coworks import entry
from coworks.globals import aws_event, aws_context


class Admin(Blueprint):

    def __init__(self, name: str = 'admin', **kwargs):
        super().__init__(name=name, **kwargs)

    @entry
    def get_route(self, pretty=False):
        """Returns the list of entrypoints with signature."""
        routes = {}
        for rule in current_app.url_map.iter_rules():
            route = {}
            for http_method in rule.methods:
                if http_method not in ['HEAD', 'OPTIONS']:
                    function_called = current_app.view_functions[rule.endpoint]
                    doc = inspect.getdoc(function_called)
                    route[http_method] = {
                        'doc': doc.replace('\n', ' ') if doc else '',
                        'signature': get_signature(function_called)
                    }
            routes[rule.rule] = route

        kwargs = {'indent': 4, 'separators': (",", ": ")} if pretty else {}
        return json.dumps({k: routes[k] for k in sorted(routes.keys())}, **kwargs)

    @entry
    def get_event(self):
        """Returns the calling context."""
        return aws_event

    @entry
    def get_context(self):
        """Returns the calling context."""
        return aws_context

    @entry
    def get_env(self):
        """Returns the stage environment."""
        return {k: v for k, v in os.environ.items()}

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
