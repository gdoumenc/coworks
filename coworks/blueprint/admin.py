import inspect
import sys
from inspect import Parameter

from jinja2 import Environment, PackageLoader, select_autoescape

from coworks import Blueprint, entry, jsonify
from coworks.utils import make_absolute


class Admin(Blueprint):

    @entry
    def get_routes(self, pretty=False):
        """Returns the list of entrypoints with signature."""
        routes = {}
        for path, entrypoint in self._current_app.entries.items():
            route = {}
            for http_method, route_entry in entrypoint.items():
                function_called = route_entry.fun
                doc = inspect.getdoc(function_called)
                route[http_method] = {
                    'doc': doc if doc else '',
                    'signature': get_signature(function_called)
                }
            routes[make_absolute(path)] = route

        return jsonify(routes, pretty)

    @entry
    def get_context(self):
        """Returns the calling context."""
        return self.current_request.to_dict()

    @entry
    def get_proxy(self):
        """Returns the calling context."""
        env = Environment(
            loader=PackageLoader(sys.modules[__name__].__name__),
            autoescape=select_autoescape(['html', 'xml']))
        env.filters["signature"] = inspect.signature
        env.filters["positional_params"] = positional_params
        env.filters["keyword_params"] = keyword_params

        data = {
            'name': self._current_app.name,
            'entries': self._current_app.entries,
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
