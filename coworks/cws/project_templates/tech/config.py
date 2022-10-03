from coworks import config


class LocalConfig(config.LocalConfig):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.environment_variables_file = ['env_vars/vars.json', 'env_vars/dev.json']


class DevConfig(config.DevConfig):

    def __init__(self,workspace='dev',  **kwargs):
        super().__init__(workspace=workspace, **kwargs)
        self.environment_variables_file = ['env_vars/vars.json', 'env_vars/dev.json']


class ProdConfig(config.ProdConfig):

    def __init__(self, **kwargs):
        super().__init__(workspace='prod', **kwargs)
        self.environment_variables_file = ['env_vars/vars.json', 'env_vars/v1.json']
