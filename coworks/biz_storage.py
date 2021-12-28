import typing as t


class BizStorage:
    S3_BUCKET = 'coworks-airflow'
    S3_PREFIX = 's3'
    DAG_ID_HEADER_KEY = 'X-CWS-DagId'
    TASK_ID_HEADER_KEY = 'X-CWS-TaskId'
    JOB_ID_HEADER_KEY = 'X-CWS-JobId'

    @staticmethod
    def get_store_bucket_key(headers) -> t.Tuple[t.Optional[str], t.Optional[str]]:
        """Returns bucket and key for asynchronous invocation."""
        biz_dag_id = headers.get(BizStorage.DAG_ID_HEADER_KEY.lower())
        biz_task_id = headers.get(BizStorage.TASK_ID_HEADER_KEY.lower())
        biz_job_id = headers.get(BizStorage.JOB_ID_HEADER_KEY.lower())
        if biz_dag_id and biz_task_id and biz_job_id:
            bucket = BizStorage.S3_BUCKET
            key = f'{BizStorage.S3_PREFIX}/{biz_dag_id}/{biz_task_id}/{biz_job_id}'
            return bucket, key
        return None, None
