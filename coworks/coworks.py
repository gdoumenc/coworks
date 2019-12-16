import inspect
from functools import update_wrapper, partial
from chalice import Chalice

from .utils import class_rest_methods, class_attribute


class MicroServiceError:
    def __init__(self, msg):
        super().__init__()
        self.__msg = msg

    @property
    def msg(self):
        return self.__msg


class TechMicroService(Chalice):

    def __init__(self, *args, **kwargs):
        # TODO Positional only argument when python 3.8 will be available on Lambda
        super().__init__(*args, **kwargs)
        self.experimental_feature_flags.update([
            'BLUEPRINTS'
        ])

        # add root route
        slug = class_attribute(self, 'slug', '')
        methods = class_rest_methods(self)
        for method, func in methods:
            if func.__name__ == method:
                route = f"{slug}"
            else:
                name = func.__name__[4:]
                route = f"{slug}/{name}" if slug else f"{name}"
            args = inspect.getfullargspec(func).args[1:]
            for arg in args:
                route = route + f"/{{{arg}}}" if route else f"{{{arg}}}"

            proxy = update_wrapper(partial(func, self), func)
            self.route(f"/{route}", methods=[method.upper()])(proxy)
