import typing as t

from airflow.models import BaseOperator
from airflow.utils.task_group import TaskGroup

from coworks.biz.operators import AsyncTechServicePullOperator
from coworks.biz.operators import TechMicroServiceOperator
from coworks.biz.sensors import AsyncTechMicroServiceSensor


class CoworksTaskGroup(TaskGroup):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__call_task: t.Optional[BaseOperator] = None
        self.__read_task: t.Optional[BaseOperator] = None

    @property
    def output(self):
        return self.read_task.output

    @property
    def call_task(self):
        return self.__call_task

    @call_task.setter
    def call_task(self, task):
        self.__call_task = task

    @property
    def read_task(self):
        return self.__read_task

    @read_task.setter
    def read_task(self, task):
        self.__read_task = task


def TechMicroServiceAsyncGroup(group_id: str, raise_errors=True, timeout=3600, **tech_kwargs):
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
            cws_task_id=f'{group_id}.call',
            raise_errors=raise_errors,
        )

    tg.call_task = call
    tg.read_task = read

    call >> wait >> read

    return tg
