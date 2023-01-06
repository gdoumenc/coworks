# noinspection PyPep8Naming
from airflow import DAG as BizMicroService
from airflow.decorators import dag

from coworks.biz.group import TechMicroServiceAsyncGroup
from coworks.biz.operators import AsyncTechServicePullOperator
from coworks.biz.operators import BranchTechMicroServiceOperator
from coworks.biz.operators import TechMicroServiceOperator
from coworks.biz.sensors import AsyncTechMicroServiceSensor
from coworks.biz.sensors import TechMicroServiceSensor


def biz(*biz_args, **biz_kwargs):
    """dag decorator redefined to create the tech microservice for triggering it in the future."""

    if 'doc_md' in biz_kwargs:
        biz_kwargs['doc_md'] += """
<img style="margin-bottom:auto;width:100px;" src="https://neorezo.io/assets/img/logo_neorezo.png"/>
"""

    def wrapper(func):
        return dag(*biz_args, **biz_kwargs)(func)

    return wrapper


_all__ = (
    AsyncTechServicePullOperator, BranchTechMicroServiceOperator, TechMicroServiceOperator,
    AsyncTechMicroServiceSensor, TechMicroServiceSensor,
    TechMicroServiceAsyncGroup,
    BizMicroService, biz,
)
