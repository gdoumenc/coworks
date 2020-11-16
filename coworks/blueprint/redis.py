import os

from coworks import Blueprint
import redis


class RedisBlueprint(Blueprint):

    def __init__(self, endpoint_env_var_name, passwd_env_var_name, port_env_var_name, **kwargs):
        super().__init__(**kwargs)
        self.redis = None

        @self.before_first_activation
        def load_env_var(*args, **kwargs):
            endpoint = os.getenv(endpoint_env_var_name)
            passwd = os.getenv(passwd_env_var_name)
            port = os.getenv(port_env_var_name)
            self.redis = redis.Redis(host=endpoint, password=passwd, port=port, db=0)
