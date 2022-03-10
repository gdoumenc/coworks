import base64
import json

from airflow.exceptions import AirflowFailException
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.sensors.base import BaseSensorOperator
from airflow.sensors.base import poke_mode_only
from airflow.utils.decorators import apply_defaults
from coworks.operators import TechMicroServiceOperator


@apply_defaults
@poke_mode_only
class TechMicroServiceSensor(BaseSensorOperator, TechMicroServiceOperator):
    """ Sensor to wait until a TechMicroservice call succeed.

    Same parameters as TechMicroServiceOperator except 'asynchronous' and 'raise_400_errors'
    """

    def __init__(self, **kwargs):
        super().__init__(asynchronous=False, raise_400_errors=False, **kwargs)

    def poke(self, context):
        self.pre_execute(context)
        res = self._call_cws(context)
        return res.ok


@apply_defaults
class AsyncTechMicroServiceSensor(BaseSensorOperator):
    """ Sensor to wait until an asynchronous TechMicroservice call is ended.

    :param cws_task_id: the tech microservice task_id awaited.
    :param xcom_push: Pushes result in XCom - result in 'json' key (default True).
    :param aws_conn_id: AWS S3 connection.
    """

    def __init__(self, *, cws_task_id: str, xcom_push_flag=False,
                 aws_conn_id: str = 'aws_s3', **kwargs):
        super().__init__(**kwargs)
        self.cws_task_id = cws_task_id
        self.xcom_push_flag = xcom_push_flag
        self.aws_conn_id = aws_conn_id

    def poke(self, context):
        ti = context['ti']
        bucket_name = ti.xcom_pull(task_ids=self.cws_task_id, key='bucket')
        bucket_key = ti.xcom_pull(task_ids=self.cws_task_id, key='key')

        self.log.info('Poking for key : s3://%s/%s', bucket_name, bucket_key)
        hook = S3Hook(aws_conn_id=self.aws_conn_id)
        res = hook.check_for_key(bucket_key, bucket_name)

        if self.xcom_push_flag:
            s3 = S3Hook(aws_conn_id=self.aws_conn_id)
            file = s3.download_file(bucket_key, bucket_name=bucket_name)
            with open(file, "r") as myfile:
                data = myfile.read()
            payload = json.loads(data)
            if payload['statusCode'] != 200:
                raise AirflowFailException("TechMicroService doesn't complete successfully")

            body = payload['body']
            if payload['isBase64Encoded']:
                body = base64.b64decode(body)

            self.xcom_push(context, 'cws_name', self.cws_name)
            self.xcom_push(context, 'status_code', payload['statusCode'])
            self.xcom_push(context, 'json', body)

        return res
