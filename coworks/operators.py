import logging
from functools import partial
from json import loads

import requests
from airflow.models.baseoperator import BaseOperator
from airflow.operators.python import BranchPythonOperator
from airflow.providers.http.hooks.http import HttpHook

from coworks.biz_storage import BizStorage


class TechMicroServiceOperator(BaseOperator):
    template_fields = ["name", "entry", "data", "json", "asynchronous"]

    def __init__(self, *, name: str = None, entry: str = None, method: str = None,
                 no_auth: bool = False, log_response: bool = False, data: dict = None, json: dict = None,
                 api_id: str = None, stage: str = None, token: str = None, directory_conn_id: str = 'neorezo_directory',
                 asynchronous: bool = False, biz_storage_class: BizStorage = BizStorage,
                 **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.entry = entry.lstrip('/')
        self.method = method.lower() if method else 'get'
        self.data = data
        self.json = json
        self.log_response = log_response
        self.asynchronous = asynchronous
        self.biz_storage_class = biz_storage_class

        # Gets url and token from name or parameters
        if name:
            http = HttpHook('get', http_conn_id=directory_conn_id)
            self.log.info("Calling CoWorks directory")
            response = http.run(name)
            if self.log_response:
                self.log.info(response.text)
            coworks_data = loads(response.text)
            token = coworks_data['token']
            self._url = f"{coworks_data['url']}/{self.entry}"
        else:
            stage = stage or "dev"
            self._url = f'https://{api_id}.execute-api.eu-west-1.amazonaws.com/{stage}/{self.entry}'

        # CReates header
        self.headers = {
            "Content-Type": 'application/json',
        }
        if not no_auth:
            self.headers['Authorization'] = token

    def execute(self, context):
        headers = self.headers
        if self.asynchronous:
            headers['InvocationType'] = 'Event'
            headers[self.biz_storage_class.DAG_ID_HEADER_KEY] = context['ti'].dag_id
            headers[self.biz_storage_class.TASK_ID_HEADER_KEY] = context['ti'].task_id
            headers[self.biz_storage_class.JOB_ID_HEADER_KEY] = context['ti'].job_id
        logging.info(f"Sending '{self.method.upper()}' to url: {self._url}")
        res = requests.request(self.method, self._url, headers=headers, data=self.data, json=self.json)
        if self.log_response:
            logging.info(res.status_code)
            logging.info(res.text)
        self.xcom_push(context, 'name', self.name)

        # Returns values or storing file
        if not self.asynchronous:
            self.xcom_push(context, 'status_code', res.status_code)
            self.xcom_push(context, 'text', res.text)
        else:
            bucket, key = self.biz_storage_class.get_store_bucket_key({k.lower(): v for k, v in headers.items()})
            self.xcom_push(context, 'bucket', bucket)
            self.xcom_push(context, 'key', key)


class BranchTechMicroServiceOperator(BranchPythonOperator):

    def __init__(self, *, service=None, on_success: str = None, on_failure: str = None, **kwargs) -> None:
        super().__init__(python_callable=lambda _: _, **kwargs)
        self.service = service
        self.on_success = on_success
        self.on_failure = on_failure

    def execute(self, context):
        self.python_callable = partial(self.branch, context, self.on_success, self.on_failure)
        return super().execute(context)

    def branch(self, context, on_success, on_failure):
        service_name = context['ti'].xcom_pull(task_ids=self.service, key='name')
        status_code = context['ti'].xcom_pull(task_ids=self.service, key='status_code')
        logging.info(f"TechMS {service_name} returned code : {status_code}")
        if status_code != 200:
            return on_failure
        return on_success
