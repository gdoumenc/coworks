import os
from collections import defaultdict

from coworks import TechMicroService, entry


class EnvTechMS(TechMicroService):
    values = defaultdict(int)
    init_value = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.any_token_authorized = True

        @self.before_first_request
        def init():
            assert os.getenv("test") is not None, "no environment variable 'test'"

    @entry
    def get(self, usage="test"):
        """Entrypoint for testing named parameter."""
        return f"Simple microservice for {usage}.\n"

    @entry
    def get_value(self, index):
        """Entrypoint for testing positional parameter."""
        return f"{self.values[index]}\n"

    @entry
    def put_value(self, index, value=0):
        self.values[index] = value
        return value

    @entry
    def get_init(self):
        return f"Initial value is {self.init_value}.\n"

    @entry
    def get_env(self):
        return f"Value of environment variable test is : {os.getenv('test')}."
