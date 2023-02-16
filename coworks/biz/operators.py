import base64
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
    :param query_params: query parameters for GET method.
    :param json: dict data for POST method.
    :param data: object to send in the body for POST method
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
    template_fields = ["cws_name", "entry", "query_params", "json", "data"]

    def __init__(self, *, cws_name: str = None, entry: str = '/', method: str = 'get', no_auth: bool = False,
                 query_params: t.Union[dict, str] = None, json: t.Union[dict, str] = None,
                 data: t.Union[dict, str] = None,
                 stage: str = None, api_id: str = None, token: str = None,
                 directory_conn_id: str = 'coworks_directory', asynchronous: bool = False,
                 xcom_push: bool = True, json_result: bool = True, raise_400_errors: bool = True,
                 accept: str = 'application/json', headers: dict = None, log_response: bool = False,
                 **kwargs) -> None:
        super().__init__(**kwargs)
        self.cws_name = cws_name
        self.entry = entry.lstrip('/')
        self.method = method.lower()
        self.no_auth = no_auth
        self.log_response = log_response
        self.query_params = query_params
        self.json = json
        self.data = data
        self.stage = stage
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
        dag_run = context['dag_run']
        start_date = dag_run.start_date.timestamp()
        trace_id = f"Root=1-{hex(int(start_date))[2:]}-{f'cws{dag_run.id:0>9}'.encode().hex()}"
        self.headers['x-amzn-trace-id'] = trace_id
        self.log.info(f"Cws trace: {trace_id}")

        if self.cws_name:
            http = HttpHook('get', http_conn_id=self.directory_conn_id)
            self.log.info("Calling CoWorks directory")
            data = {'stage': self.stage} if self.stage else {}
            response = http.run(self.cws_name, data=data)
            coworks_data = loads(response.text)
            self.token = coworks_data['token']
            self._url = f"{coworks_data['url']}/{self.entry}"
        else:
            self._url = f'https://{self.api_id}.execute-api.eu-west-1.amazonaws.com/{self.stage}/{self.entry}'

        if self.asynchronous:
            ti = context['ti']
            self._bucket = 'coworks-airflow'
            self._key = f"s3/{dag_run.dag_id}/{ti.task_id}/{ti.job_id}"

            self.headers['InvocationType'] = 'Event'
            self.headers['X-CWS-S3Bucket'] = self._bucket
            self.headers['X-CWS-S3Key'] = self._key
            self.log.info(f"Result stored in 's3://{self._bucket}/{self._key}'")

        if not self.no_auth:
            self.headers['Authorization'] = self.token

    def execute(self, context):
        """Call TechMicroService.
        """
        resp = self._call_cws(context)
        if self.xcom_push_flag:
            self._push_response(context, resp)

    def _call_cws(self, context):
        """Method used by operator and sensor."""
        self.log.info(f"Calling {self.method.upper()} method to {self._url}")
        resp = requests.request(
            self.method.upper(), self._url, headers=self.headers,
            params=self.query_params, json=self.json, data=self.data
        )
        self.log.info(f"Resulting status code : {resp.status_code}")

        # Manages status
        if self.raise_400_errors and resp.status_code >= 400:
            self.log.error(f"Bad request: {resp.text}'")
            raise AirflowFailException(f"The TechMicroService {self.cws_name} had a client error {resp.status_code}!")
        if resp.status_code >= 500:
            self.log.error(f"Internal error: {resp.text}'")
            raise AirflowFailException(
                f"The TechMicroService {self.cws_name} had an internal error {resp.status_code}!")
        return resp

    def _push_response(self, context, resp):
        # Return values or store file information
        self.xcom_push(context, XCOM_CWS_NAME, self.cws_name or self.api_id)
        if self.asynchronous:
            self.xcom_push(context, XCOM_CWS_BUCKET, self._bucket)
            self.xcom_push(context, XCOM_CWS_KEY, self._key)
        else:
            if self.json_result:
                try:
                    returned_value = resp.json() if resp.content else {}
                except JSONDecodeError:
                    self.log.error(f"Not a JSON value: {resp.text}'")
                    returned_value = resp.text
            else:
                returned_value = resp.text

            if self.log_response:
                self.log.info(returned_value)

            self.xcom_push(context, XCOM_STATUS_CODE, resp.status_code)
            self.xcom_push(context, 'return_value', returned_value)


class AsyncTechServicePullOperator(BaseOperator):
    """Pull in XCom a microservice result when its was called asynchronously.

    :param cws_task_id: the tech microservice called asynchronously.
    :param aws_conn_id: aws connection (default 'aws_s3').
    :param raise_errors: raises error if the called microserrvice did (default True).
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
            self.log.error(f"Error: {payload['body']}'")
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

    def __init__(self, *, cws_task_id: str = None, on_success: t.Union[str, t.Iterable[str]] = None,
                 on_failure: t.Union[str, t.Iterable[str]] = None, on_no_content: t.Union[str, t.Iterable[str]] = None,
                 response_check: t.Optional[t.Callable[..., bool]] = None, on_check: str = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.cws_task_id = cws_task_id
        self.on_success = on_success
        self.on_failure = on_failure
        self.on_no_content = on_no_content
        self.response_check = response_check
        self.on_check = on_check

    def choose_branch(self, context):
        status_code = int(context['ti'].xcom_pull(task_ids=self.cws_task_id, key=XCOM_STATUS_CODE))
        self.log.info(f"TechMS {self.cws_task_id} returned code : {status_code}")
        if self.on_failure and status_code >= 400:
            return self.on_failure
        if self.on_no_content and status_code == 204:
            return self.on_no_content
        if self.on_check and self.response_check:
            text = int(context['ti'].xcom_pull(task_ids=self.cws_task_id))
            if self.response_check(text):
                return self.on_check
        return self.on_success
