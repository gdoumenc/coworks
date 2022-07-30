import base64
import logging
import typing as t
from json import JSONDecodeError
from json import loads

import requests
from airflow.exceptions import AirflowFailException
from airflow.models.baseoperator import BaseOperator
from airflow.operators.branch import BaseBranchOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.http.hooks.http import HttpHook

XCOM_CWS_BUCKET = 'bucket'  # the AWS S3 bucket where the coworks techmicroservice result is stored
XCOM_CWS_KEY = 'key'  # the AWS S3 key where the coworks techmicroservice result is stored
XCOM_CWS_NAME = 'cws_name'
XCOM_STATUS_CODE = 'status_code'


class TechMicroServiceOperator(BaseOperator):
    """Microservice operator.
    The tech microservice may be called from its name or from it api_id, stage and token.

    :param cws_name: the tech microservice name.
    :param entry: the route entry.
    :param method: the route method ('GET', 'POST').
    :param no_auth: set to 'True' if no authorization is needded (default 'False').
    :param data: data for GET method (use data keyword as request 'params' keyword is used in Airflow)
    :param json: data for POST method.
    :param stage: the microservice stage (default 'dev' if 'cws_name' not defined).
    :param api_id: APIGateway id (must be defined if no 'cws_name').
    :param token: Authorization token (must be defined if auth and no 'cws_name').
    :param directory_conn_id: Connection defined for the directory service (default 'coworks_directory').
    :param asynchronous: Asynchronous call (default False).
    :param xcom_push: Pushes result in XCom (default True).
    :param json_result: Returns a JSON value in 'return_value' (default True).
    :param raise_400_errors: raise error on client 400 errors (default True).
    :param accept: accept header value (default 'application/json').
    :param headers: specific header values forced (default {}).
    :param log_response: Trace result content (default False).
    """
    template_fields = ["cws_name", "entry", "data", "json", "asynchronous"]

    def __init__(self, *, cws_name: str = None, entry: str = None, method: str = None, no_auth: bool = False,
                 data: t.Union[dict, str] = None, json: t.Union[dict, str] = None,
                 stage: str = None, api_id: str = None, token: str = None,
                 directory_conn_id: str = 'coworks_directory', asynchronous: bool = False,
                 xcom_push=True, json_result=True, raise_400_errors: bool = True, accept='application/json',
                 headers=None, log_response: bool = False,
                 **kwargs) -> None:
        super().__init__(**kwargs)
        self.cws_name = cws_name
        self.entry = entry.lstrip('/')
        self.method = method.lower() if method else 'get'
        self.no_auth = no_auth
        self.log_response = log_response
        self.data = data
        self.json = json
        self.stage = stage or "dev"
        self.api_id = api_id
        self.token = token
        self.directory_conn_id = directory_conn_id
        self.asynchronous = asynchronous
        self.xcom_push_flag = xcom_push
        self.json_result = json_result
        self.raise_400_errors = raise_400_errors
        self._url = self._bucket = self._key = None

        if not self.cws_name and not self.api_id:
            raise AirflowFailException(f"The APIGateway id must be defined! (param 'api_id')")
        if not no_auth and not self.cws_name and not self.token:
            raise AirflowFailException(f"The authorization token id must be defined! (param 'token')")

        # Creates header
        self.headers = {
            'Content-Type': "application/json",
            'Accept': accept,
        }
        if headers:
            self.headers.update(headers)

    def pre_execute(self, context):
        """Gets url and token from name or parameters.
        Done only before execution not on DAG loading.
        """
        if self.cws_name:
            http = HttpHook('get', http_conn_id=self.directory_conn_id)
            self.log.info("Calling CoWorks directory")
            response = http.run(self.cws_name)
            if self.log_response:
                self.log.info(response.text)
            coworks_data = loads(response.text)
            self.token = coworks_data['token']
            self._url = f"{coworks_data['url']}/{self.entry}"
        else:
            self._url = f'https://{self.api_id}.execute-api.eu-west-1.amazonaws.com/{self.stage}/{self.entry}'

        if self.asynchronous:
            self._bucket = 'coworks-airflow'
            self._key = f"s3/{context['ti'].dag_id}/{context['ti'].task_id}/{context['ti'].job_id}"

            self.headers['InvocationType'] = 'Event'
            self.headers['X-CWS-S3Bucket'] = self._bucket
            self.headers['X-CWS-S3Key'] = self._key
            logging.info(f"Result stored in 's3://{self._bucket}/{self._key}'")

        if not self.no_auth:
            self.headers['Authorization'] = self.token

    def execute(self, context):
        """Call TechMicroService.
        """
        self._call_cws(context)

    def _call_cws(self, context):
        logging.info(f"Calling {self.method.upper()} method to {self._url}")
        res = requests.request(self.method.upper(), self._url, headers=self.headers, data=self.data, json=self.json)
        logging.info(f"Resulting status code : {res.status_code}")

        # Manages status
        if self.raise_400_errors and res.status_code >= 400:
            logging.error(f"Bad request: {res.text}'")
            raise AirflowFailException(f"The TechMicroService {self.cws_name} had a client error {res.status_code}!")
        if res.status_code >= 500:
            logging.error(f"Internal error: {res.text}'")
            raise AirflowFailException(f"The TechMicroService {self.cws_name} had an internal error {res.status_code}!")

        # Return values or store file information
        if self.xcom_push_flag:
            self.xcom_push(context, XCOM_CWS_NAME, self.cws_name or self.api_id)
            if self.asynchronous:
                self.xcom_push(context, XCOM_CWS_BUCKET, self._bucket)
                self.xcom_push(context, XCOM_CWS_KEY, self._key)
            else:
                if self.json_result:
                    try:
                        returned_value = res.json() if res.content else {}
                    except JSONDecodeError:
                        logging.error(f"Not a JSON value: {res.text}'")
                        returned_value = res.text
                else:
                    returned_value = res.text

                if self.log_response:
                    logging.info(returned_value)

                self.xcom_push(context, XCOM_STATUS_CODE, res.status_code)
                self.xcom_push(context, 'return_value', returned_value)
                return returned_value


class AsyncTechServicePullOperator(BaseOperator):
    """Pull in XCom a microservice result when its was called asynchronously.

    :param cws_task_id: the tech microservice called asynchronously.
    :param aws_conn_id: aws connection (default 'aws_s3').
    """

    def __init__(self, *, cws_task_id: str = None, aws_conn_id: str = 'aws_s3',
                 raise_errors: bool = True, **kwargs) -> None:
        super().__init__(**kwargs)
        self.cws_task_id = cws_task_id
        self.aws_conn_id = aws_conn_id
        self.raise_errors = raise_errors

    def execute(self, context):
        ti = context["ti"]

        # Reads bucket file content
        bucket_name = ti.xcom_pull(task_ids=self.cws_task_id, key=XCOM_CWS_BUCKET)
        key = ti.xcom_pull(task_ids=self.cws_task_id, key=XCOM_CWS_KEY)
        s3 = S3Hook(aws_conn_id=self.aws_conn_id)
        file = s3.download_file(key, bucket_name=bucket_name)
        with open(file, "r") as myfile:
            data = myfile.read()
        payload = loads(data)

        status_code = payload['statusCode']

        if self.raise_errors and status_code >= 300:
            raise AirflowFailException(f"TechMicroService doesn't complete successfully: {status_code}")

        self.xcom_push(context, XCOM_STATUS_CODE, status_code)
        if payload['isBase64Encoded']:
            return base64.b64decode(payload['body'])
        return payload['body']


class BranchTechMicroServiceOperator(BaseBranchOperator):
    """Branch operator based on TechMicroservice call.

    :param cws_task_id: the tech microservice task_id result tested to determine the branch.
    :param on_failure: the task_ids in case of status code returned >= 400.
    :param on_no_content: the task_ids in case of status code returned == 204.
    :param response_check: function evaluated in case of success and on_check defined.
    :param on_check: the task_ids in case of status code returned == 200 and response checked.
    :param on_success: the task_ids in case of status code returned == 200 and on check branch not selected.
    """

    def __init__(self, *, cws_task_id: str = None, on_success: str = None, on_failure: str = None,
                 on_no_content: str = None, response_check: t.Optional[t.Callable[..., bool]] = None,
                 on_check: str = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.cws_task_id = cws_task_id
        self.on_success = on_success
        self.on_failure = on_failure
        self.on_no_content = on_no_content
        self.response_check = response_check
        self.on_check = on_check

    def choose_branch(self, context):
        status_code = int(context['ti'].xcom_pull(task_ids=self.cws_task_id, key=XCOM_STATUS_CODE))
        logging.info(f"TechMS {self.cws_task_id} returned code : {status_code}")
        if self.on_failure and status_code >= 400:
            return self.on_failure
        if self.on_no_content and status_code == 204:
            return self.on_no_content
        if self.on_check and self.response_check:
            text = int(context['ti'].xcom_pull(task_ids=self.cws_task_id))
            if self.response_check(text):
                return self.on_check
        return self.on_success
