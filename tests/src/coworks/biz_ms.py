from coworks import BizMicroService


class BizMS(BizMicroService):
    def __init__(self):
        super().__init__('step_function', ms_name='biz')
