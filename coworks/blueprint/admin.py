import inspect

from coworks import Blueprint, jsonify


class Admin(Blueprint):

    def get_routes(self, pretty=False):
        """Returns the list of entrypoints with signature."""
        app = self._current_app
        routes = {}
        for resource_path, entry in app.routes.items():
            route = {}
            for http_method, route_entry in entry.items():
                function_called = route_entry.view_function
                doc = inspect.getdoc(function_called)
                route[http_method] = {
                    'doc': doc if doc else '',
                    'signature': get_signature(function_called.__cws_func__)
                }
            routes[resource_path] = route

        return jsonify(routes, pretty)

    def get_context(self):
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
