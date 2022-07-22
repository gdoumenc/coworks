import typing as t

from airflow.models import BaseOperator
from airflow.utils.task_group import TaskGroup

from coworks.biz.operators import AsyncTechServicePullOperator
from coworks.biz.operators import TechMicroServiceOperator
from coworks.biz.sensors import AsyncTechMicroServiceSensor


class CoworksTaskGroup(TaskGroup):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__read_task: t.Optional[BaseOperator] = None

    @property
    def output(self):
        return self.read_task.output

    @property
    def read_task(self):
        return self.__read_task

    @read_task.setter
    def read_task(self, task):
        self.__read_task = task


def TechMicroServiceAsyncGroup(group_id: str, timeout=3600, **tech_kwargs):
    """Task group to allow asynchronous call of a TechMicroService.

    The returned value is defined in the task_id : '{group_id}.read'.
    """
    with CoworksTaskGroup(group_id=group_id) as tg:
        call = TechMicroServiceOperator(
            task_id="call",
            asynchronous=True,
            **tech_kwargs,
        )
        wait = AsyncTechMicroServiceSensor(
            task_id='wait',
            cws_task_id=f'{group_id}.call',
            timeout=timeout,
        )
        read = AsyncTechServicePullOperator(
            task_id='read',
            cws_task_id=f'{group_id}.call'
        )

    call >> wait >> read

    tg.read_task = read

    return tg
