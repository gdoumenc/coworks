import inspect

from coworks import Blueprint, entry, jsonify
from coworks.utils import make_absolute


class Admin(Blueprint):

    @entry
    def get_routes(self, pretty=False):
        """Returns the list of entrypoints with signature."""
        app = self._current_app
        routes = {}
        for path, entrypoint in app.entries.items():
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
        return self.current_request.to_dict()


def get_signature(func):
    sig = ""
    params = inspect.signature(func).parameters
    index = 0
    for k, p in params.items():
        index += 1
        if index == 1:
            continue
        sp = k
        if p.annotation != inspect.Parameter.empty:
            sp = f"{sp}:{str(p.annotation)}"
        if p.default != inspect.Parameter.empty:
            sp = f"{sp}={p.default}"
        sig = f"{sp}" if index == 2 else f"{sig}, {sp}"
    return f"({sig})"
