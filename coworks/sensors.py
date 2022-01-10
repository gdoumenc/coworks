from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.sensors.base import BaseSensorOperator
from airflow.utils.decorators import apply_defaults


@apply_defaults
class AsyncTechMicroServiceSensor(BaseSensorOperator):
    """ Sensor to wait until an asynchronous TechMicroservice call is ended.

        :param cws_task_id: the tech microservice task_id awaited.
        :param aws_conn_id: AWS S3 connection.
        """

    def __init__(self, *, cws_task_id: str, aws_conn_id: str = 'aws_s3', **kwargs):
        super().__init__(**kwargs)
        self.cws_task_id = cws_task_id
        self.aws_conn_id = aws_conn_id

    def poke(self, context):
        ti = context['ti']
        bucket_name = ti.xcom_pull(task_ids=self.cws_task_id, key='bucket')
        bucket_key = ti.xcom_pull(task_ids=self.cws_task_id, key='key')
        self.log.info('Poking for key : s3://%s/%s', bucket_name, bucket_key)
        hook = S3Hook(aws_conn_id=self.aws_conn_id)
        return hook.check_for_key(bucket_key, bucket_name)
