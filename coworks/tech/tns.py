import json
import os
import traceback

import boto3
import requests
from chalice import Chalice, BadRequestError

app = Chalice(app_name="app")


@app.lambda_function(name="call")
def call_url(event, context):
    from aws_xray_sdk.core.lambda_launcher import LAMBDA_TRACE_HEADER_KEY
    from aws_xray_sdk.core.models.trace_header import TraceHeader
    from aws_xray_sdk.core.context import Context
    from aws_xray_sdk.core import xray_recorder, patch

    libraries = (['botocore', 'requests'])
    patch(libraries)

    # Set X-Ray trace data
    x_ray = event.get('XRay')
    ms_name = event.get('MSName', 'no name')
    if x_ray:
        root_id = x_ray.get('Root')
        parent_id = x_ray.get('Parent')
        trace_header = TraceHeader(root=root_id, parent=parent_id)
    else:
        header_str = os.getenv(LAMBDA_TRACE_HEADER_KEY)
        trace_header = TraceHeader.from_header_str(header_str)
        root_id = trace_header.root
        parent_id = trace_header.parent

    # XRay segment
    xray_recorder.configure(service='coworks-step-function', context=Context())
    segment = xray_recorder.begin_segment(f"{ms_name} Step Function call", traceid=root_id, parent_id=parent_id)
    try:
        # Get invoke parameters
        environment = event.get('environment')
        invoke_params = event.get('invoke_params')
        query_params = invoke_params.get('query_params', {})
        body_params = invoke_params.get('body_params', {})
        headers = invoke_params.get('headers', {})
        inputs = event.get('inputs')
        output = event.get('output')

        # Get S3 streamed parameters
        kwargs = {}
        if inputs:
            # subsegment = xray_recorder.begin_segment('Get streamed parameters')
            for input in inputs:
                aws_access_key_id = environment.get('aws_access_key_id', {})
                aws_secret_access_key = environment.get('aws_secret_access_key', {})
                region_name = environment.get('region_name', {})
                bucket = input.get('bucket')
                key = input.get('key')
                boto_session = boto3.Session(aws_access_key_id, aws_secret_access_key,
                                             region_name=region_name)
                s3_client = boto_session.client('s3')
                uploaded_object = s3_client.get_object(Bucket=bucket, Key=key)
                if not uploaded_object:
                    return BadRequestError(f"No key '{key}' in bucket '{bucket}'")
                value = uploaded_object['Body'].read().decode('utf-8')
                print(value)
                print(type(value))
                kwargs[input['name']] = value
            # subsegment.put_metadata('streams', kwargs.keys(), "my namespace")
            # xray_recorder.end_segment()

        # Calls APIGateway url
        http_method = invoke_params.get('http_method')
        if not http_method:
            raise BadRequestError("http method parameter not defined")
        method = getattr(requests, http_method.lower())
        if not method:
            raise BadRequestError(f"Undefined http method {http_method}")
        url = invoke_params.get('url')
        if not url:
            raise BadRequestError("url method parameter not defined")

        if query_params:
            for name, content in kwargs.items():
                query_params[name] = content
        if body_params:
            for name, content in kwargs.items():
                body_params[name] = content
            # use JSONPath to change value

        # Uses same trace id of the first call, set metadata and invko microservice
        headers['X-Amzn-Trace-Id'] = trace_header.to_header_str()
        for key, value in event.items():
            segment.put_metadata(key, value, ms_name)
        resp = _call_url(method, url, params=query_params, json=body_params, headers=headers)
        segment.put_metadata('call_result', resp.text, ms_name)
        xray = {'root': root_id, 'parent': segment.id}
        resp.raise_for_status()

        # Stores S3 streamed parameters
        if output:
            # subsegment = xray_recorder.begin_subsegment('Put streamed output')
            aws_access_key_id = environment.get('aws_access_key_id', {})
            aws_secret_access_key = environment.get('aws_secret_access_key', {})
            region_name = environment.get('region_name', {})
            bucket = output.get('bucket', "morassuti-sfn")
            key = output.get('key', "stock_armony")
            boto_session = boto3.Session(aws_access_key_id, aws_secret_access_key,
                                         region_name=region_name)
            s3_client = boto_session.client('s3')
            s3_client.put_object(Bucket=bucket, Key=key, Body=resp.text)
            # subsegment.put_metadata("Output stream", {'Bucket': bucket, 'Key': key}, "my namespace")
            # xray_recorder.end_subsegment()

            result = {'bucket': bucket, 'key': key}
            return {'result': result, 'xray': xray}

        try:
            return {'result': resp.json(), 'xray': xray}
        except json.JSONDecodeError:
            return resp.content
    except Exception as e:
        print(f"Exception : {str(e)}")
        traceback.print_stack()
        segment.add_exception(e, traceback.extract_stack())
        raise
    finally:
        xray_recorder.end_segment()


def _call_url(method, url, params, json, headers):
    if not url:
        raise BadRequestError(f"Undefined url {url}.")

    if params:
        return method(url, params=params, headers=headers)
    if json:
        return method(url, json=json, headers=headers)
    return method(url, headers=headers)
