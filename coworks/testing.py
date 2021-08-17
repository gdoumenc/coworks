from flask.testing import FlaskClient


class CoworksClient(FlaskClient):

    def __init__(self, app, *args, **kwargs):
        """Disable default exception handler for internal code."""
        def handle_exception(e):
            raise e

        app.handle_exception = handle_exception
        super().__init__(app, *args, **kwargs)

    def get(self, url, *args, params=None, **kw):
        return super().get(self._add_params(url, params=params), *args, **kw)

    def post(self, url, *args, params=None, **kw):
        return super().post(self._add_params(url, params=params), *args, **kw)

    def put(self, url, *args, params=None, **kw):
        return super().put(self._add_params(url, params=params), *args, **kw)

    def _add_params(self, url, params=None):
        if params is not None:
            url += '?'
            for i, (k, v) in enumerate(params.items()):
                if i:
                    url += '&'
                if type(v) is list:
                    for i, vl in enumerate(v):
                        if i:
                            url += '&'
                        url += f"{k}={vl}"
                else:
                    url += f"{k}={v}"
        return url
