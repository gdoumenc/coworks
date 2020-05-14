import cgi
import io
import json
import os
import sys
import traceback
from functools import update_wrapper

import boto3
from botocore.exceptions import BotoCoreError
from chalice import BadRequestError, Response
from requests_toolbelt.multipart import MultipartDecoder

from coworks.utils import begin_xray_subsegment, end_xray_subsegment


class CoworksMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.debug = kwargs.pop('debug', False)

        self.aws_s3_sfn_data_session = AwsS3Session(env_var_access_key="AWS_RUN_ACCESS_KEY_ID",
                                                    env_var_secret_key="AWS_RUN_SECRET_KEY",
                                                    env_var_region="AWS_RUN_REGION")
        self.aws_s3_form_data_session = AwsS3Session(env_var_access_key="AWS_FORM_DATA_ACCESS_KEY_ID",
                                                     env_var_secret_key="AWS_FORM_DATA_SECRET_KEY",
                                                     env_var_region="AWS_FORM_DATA_REGION")

    def _create_rest_proxy(self, func, kwarg_keys, args, varkw):
        original_app_class = self.__class__

        def proxy(**kws):
            if self.debug:
                print(f"Calling {func} for {self}")

            subsegment = begin_xray_subsegment(f"{func.__name__} microservice")
            try:
                if subsegment:
                    subsegment.put_metadata('headers', self.current_request.headers, "CoWorks")

                # Renames positionnal parameters (index added in label)
                kwargs = {}
                for kw, value in kws.items():
                    param = args[int(kw[1:])]
                    kwargs[param] = value

                # Adds kwargs parameters
                def check_param_expected_in_lambda(param_name):
                    """Alerts when more parameters than expected are defined in request."""
                    if param_name not in kwarg_keys and varkw is None:
                        raise BadRequestError(f"TypeError: got an unexpected keyword argument '{param_name}'")

                def add_param(param_name, param_value):
                    check_param_expected_in_lambda(param_name)
                    if param_name in params:
                        if isinstance(params[param_name], list):
                            params[param_name].append(param_value)
                        else:
                            params[param_name] = [params[param_name], param_value]
                    else:
                        params[param_name] = param_value

                req = self.current_request
                if kwarg_keys or varkw:
                    params = {}
                    if req.raw_body:  # POST request
                        content_type = req.headers['content-type']
                        if content_type.startswith('multipart/form-data'):
                            try:
                                multipart_decoder = MultipartDecoder(req.raw_body, content_type)
                                for part in multipart_decoder.parts:
                                    name, content = self._get_multipart_content(part)
                                    add_param(name, content)
                            except Exception as e:
                                print(e)
                            kwargs = dict(**kwargs, **params)

                        elif content_type.startswith('application/json'):
                            if hasattr(req.json_body, 'items'):
                                params = {}
                                for k, v in req.json_body.items():
                                    add_param(k, v)
                                kwargs = dict(**kwargs, **params)
                            else:
                                kwargs[kwarg_keys[0]] = req.json_body
                        elif content_type.startswith('text/plain'):
                            kwargs[kwarg_keys[0]] = req.json_body
                        else:
                            BadRequestError(f"Cannot manage content type {content_type} for {self}")

                    else:  # GET request

                        # adds parameters from qurey parameters
                        for k in req.query_params or []:
                            value = req.query_params.getlist(k)
                            add_param(k, value if len(value) > 1 else value[0])
                        kwargs = dict(**kwargs, **params)

                if self.debug:
                    print(f"Calling {self} with event {kwargs}")

                # chalice is changing class for local server for threading reason (why not mixin..?)
                self_class = self.__class__
                if self_class != original_app_class:
                    self.__class__ = original_app_class
                resp = func(self, **kwargs)
                self.__class__ = self_class

                return _convert_response(resp)

            except Exception as e:
                print(f"Exception : {str(e)}")
                traceback.print_exc()
                if subsegment:
                    subsegment.add_exception(e, traceback.extract_stack())
                raise BadRequestError(str(e))
            finally:
                end_xray_subsegment()

        proxy = update_wrapper(proxy, func)
        proxy.__class_func__ = func
        return proxy

    def _get_multipart_content(self, part):
        headers = {k.decode('utf-8'): cgi.parse_header(v.decode('utf-8')) for k, v in part.headers.items()}
        content = part.content
        _, content_disposition_params = headers['Content-Disposition']
        part_content_type, _ = headers.get('Content-Type', (None, None))
        name = content_disposition_params['name']

        # content in a text or json value
        if 'filename' not in content_disposition_params:
            if part_content_type == 'application/json':
                return name, self._get_data_on_s3(json.loads(content.decode('utf-8')))
            return name, self._get_data_on_s3(content.decode('utf-8'))

        # content in a file (s3 or plain text)
        if part_content_type == 'text/s3':
            pathes = content.decode('utf-8').split('/', 1)
            try:
                s3_object = self.aws_s3_form_data_session.client.get_object(Bucket=pathes[0], Key=pathes[1])
            except BotoCoreError:
                print(f"Bucket={pathes[0]} Key={pathes[1]} not found on s3")
                return BadRequestError(f"Bucket={pathes[0]} Key={pathes[1]} not found on s3")
            file = io.BytesIO(s3_object['Body'].read())
            mime_type = s3_object['ContentType']
        else:
            file = io.BytesIO(content)
            mime_type = part_content_type
        file.name = content_disposition_params['filename']

        return name, FileParam(file, mime_type)

    def _set_multipart_content(self, form_data):
        def encode_part(_part):
            if type(_part) is str:
                return None, _part, 'text/plain'

            if 'mime_type' in _part:
                mime_type = _part.get('mime_type')
            elif 'json' in _part:
                _part['content'] = _part.get('json')
                mime_type = 'application/json'
            elif 's3' in _part:
                path = _part.get('s3')
                _part['filename'] = path.split('/')[-1]
                _part['path'] = path
                mime_type = 'text/s3'
            else:
                mime_type = 'text/plain'

            filename = _part.get('filename')
            if mime_type == 'text/plain':
                content = _part.get('content')
                return filename, content, mime_type
            elif mime_type == 'application/json':
                content = _part.get('content')
                return filename, json.dumps(content), mime_type
            elif mime_type == 'text/s3':
                path = _part.get('path')
                return filename, path, mime_type
            else:
                raise BadRequestError(f"Undefined mime type {mime_type}")

        parts = []
        for name, part in form_data.items():
            if type(part) is list:
                parts.extend([(name, encode_part(p)) for p in part])
            else:
                parts.append((name, encode_part(part)))
        return parts

    def _set_data_on_s3(self, data):
        """Saves value on S3 temporary file if content is too big."""

        def set_on_s3(value):
            s3_client = self.aws_s3_sfn_data_session.client
            context = self.lambda_context
            key = f"tmp/{context.aws_request_id}"
            tags = f"Name={context.function_name}"
            s3_client.put_object(Bucket="coworks-microservice", Key=key, Body=value, Tagging=tags)
            return f"$${key}$$"

        if type(data) == str:
            return set_on_s3(data) if len(data) > 1000 else data
        if type(data) == list:
            return [self._set_data_on_s3(v) for v in data]
        if type(data) == dict:
            for k, v in data.items():
                data[k] = self._set_data_on_s3(v)
        return data

    def _get_data_on_s3(self, data):
        """Retrieves value from S3 temporary file (content too big)."""

        def get_on_s3(value):
            s3_client = self.aws_s3_sfn_data_session.client
            s3_object = s3_client.get_object(Bucket="coworks-microservice", Key=value[2:-2])
            return s3_object['Body'].read().decode("utf-8")

        if type(data) == str:
            return get_on_s3(data) if data.startswith('$$') and data.endswith('$$') else data
        if type(data) == list:
            return [self._get_data_on_s3(v) for v in data]
        if type(data) == dict:
            for k, v in data.items():
                data[k] = self._get_data_on_s3(v)
        return data


def _convert_response(resp):
    if type(resp) is tuple:
        status_code = resp[1]
        if len(resp) == 2:
            return Response(body=resp[0], status_code=status_code)
        else:
            return Response(body=resp[0], status_code=status_code, headers=resp[2])

    elif not isinstance(resp, Response):
        return Response(body=resp)

    return resp


class Boto3Mixin:

    def __init__(self, service='s3', profile_name=None, env_var_access_key='aws_access_key_id',
                 env_var_secret_key='aws_secret_access_key', env_var_region='aws_region',
                 **kwargs):
        super().__init__(**kwargs)
        self.__session__ = self.__client__ = None
        self.__service = service
        self.__env_var_access_key = env_var_access_key
        self.__env_var_secret_key = env_var_secret_key
        self.__env_var_region = env_var_region

        self.__profile_name = profile_name

    @property
    def aws_access_key(self):
        value = os.getenv(self.__env_var_access_key)
        if not value:
            print(f"{self.__env_var_access_key} not defined in environment")
            raise EnvironmentError(f"{self.__env_var_access_key} not defined in environment")
        return value

    @property
    def aws_secret_access_key(self):
        value = os.getenv(self.__env_var_secret_key)
        if not value:
            print(f"{self.__env_var_secret_key} not defined in environment")
            raise EnvironmentError(f"{self.__env_var_secret_key} not defined in environment")
        return value

    @property
    def region_name(self):
        value = os.getenv(self.__env_var_region)
        if not value:
            print(f"{self.__env_var_region} not defined in environment")
            raise EnvironmentError(f"{self.__env_var_region} not defined in environment")
        return value

    @property
    def client(self):
        if self.__client__ is None:
            self.__client__ = self.__session.client(self.__service)
        return self.__client__

    @property
    def __session(self):
        if self.__session__ is None:
            region_name = self.region_name
            if self.__profile_name is not None:
                try:
                    self.__session__ = boto3.Session(profile_name=self.__profile_name, region_name=region_name)
                except Exception:
                    print(f"Cannot create session for profile {self.__profile_name} and region {region_name}")
                    raise
            else:
                access_key = self.aws_access_key
                secret_key = self.aws_secret_access_key
                try:
                    self.__session__ = boto3.Session(access_key, secret_key, region_name=region_name)
                except Exception:
                    print(f"Cannot create session for key {access_key}, secret {secret_key} and region {region_name}")
                    raise
        return self.__session__


class FileParam:

    def __init__(self, file, mime_type):
        self.file = file
        self.mime_type = mime_type

    def __repr__(self):
        if self.mime_type:
            return f'FileParam({self.file.name}, {self.mime_type})'
        return f'FileParam({self.file.name})'


class AwsS3Session(Boto3Mixin):

    def __init__(self, **kwargs):
        super().__init__(service='s3', **kwargs)


class AwsSFNSession(Boto3Mixin):

    def __init__(self, **kwargs):
        super().__init__(service='stepfunctions', **kwargs)
