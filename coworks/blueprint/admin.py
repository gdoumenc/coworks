import inspect

from coworks import Blueprint


class Admin(Blueprint):

    def get_routes(self):
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
                    'signature': str(inspect.signature(function_called.__class_func__))
                }
            routes[resource_path] = route
        return routes

    def get_context(self):
        """Returns the calling context."""
        return self.current_request.to_dict()
