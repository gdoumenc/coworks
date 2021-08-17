from coworks import BizMicroService, entry
from coworks.config import LocalConfig


class BizMS(BizMicroService):
    def __init__(self, configs=None):
        super().__init__(name='biz', configs=configs or LocalConfig())

    @entry
    def get(self, name='ok'):
        return name, 200
