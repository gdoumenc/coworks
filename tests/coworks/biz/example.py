from coworks import BizFactory, Every
from coworks.cws.sfn import StepFunctionWriter

biz = BizFactory(ms_name='biz')
reactor1 = biz.create('small', 'often', Every(1, Every.DAYS))
reactor2 = biz.create('complete', 'often', Every(1, Every.DAYS))
reactor3 = biz.create('complete', 'rarely', Every(365, Every.DAYS))
StepFunctionWriter(biz)
