from coworks import BizMicroService, entry


class BizMS(BizMicroService):

    @entry
    def get(self, name='ok'):
        return name, 200
