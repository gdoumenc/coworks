import typing as t

from airflow.models import BaseOperator
from airflow.operators.python import PythonOperator
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


def TechMicroServiceAsyncGroup(group_id: str, transformer: t.Callable = None,
                               op_args: t.Optional[t.Collection[t.Any]] = None,
                               op_kwargs: t.Optional[t.Mapping[str, t.Any]] = None,
                               method: str = 'get',
                               raise_errors: bool = True, timeout: int = 900, xcom_push: bool = True,
                               **tech_kwargs):
    """Task group to allow asynchronous call of a TechMicroService.

    The returned value is defined in the task_id : '{group_id}.read'.

    :param group_id: group id.
    :param transformer: python transformer function.
    :param op_args: python transformer args.
    :param op_kwargs: python transformer kwargs.
    :param method: microservice method called.
    :param raise_errors: raises error if microservice call raised one.
    :param timeout: asynchronous call timeout.
    :param xcom_push:  Pushes result in XCom (default True).

    .. versionchanged:: 0.8.0
        Added the ``transformer`` parameter.
    """
    with CoworksTaskGroup(group_id=group_id) as tg:
        if transformer:
            transformer_task = PythonOperator(
                task_id=transformer.__name__,
                python_callable=transformer,
                op_args = op_args,
                op_kwargs = op_kwargs
            )

            if method.lower() == 'get':
                if 'query_params' in tech_kwargs:
                    transformer_task.log.warning(f"Calling transformer method with already query_params parameter call")
                tech_kwargs['query_params'] = transformer_task.output
            else:
                if 'json' in tech_kwargs:
                    transformer_task.log.warning("Calling transformer method with already json parameter call")
                tech_kwargs['json'] = transformer_task.output

        call = TechMicroServiceOperator(
            task_id="call",
            asynchronous=True,
            method=method,
            **tech_kwargs,
        )
        wait = AsyncTechMicroServiceSensor(
            task_id='wait',
            cws_task_id=f'{group_id}.call',
            timeout=timeout,
        )

        if xcom_push:
            read = AsyncTechServicePullOperator(
                task_id='read',
                cws_task_id=f'{group_id}.call',
                raise_errors=raise_errors,
            )

    tg.call_task = call
    call >> wait

    if transformer:
        tg.transformer_task = transformer_task
        transformer_task >> call
    if xcom_push:
        tg.read_task = read
        wait >> read

    return tg
