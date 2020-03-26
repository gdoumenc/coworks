import cgi
import urllib.parse

import jinja2
from chalice import Response, NotFoundError
from requests_toolbelt.multipart import decoder

from coworks import TechMicroService
from ..mixins import Boto3Mixin


class S3Loader(jinja2.BaseLoader, Boto3Mixin):

    def __init__(self, bucket):
        super().__init__()
        self.__s3_client__ = None
        self.bucket = bucket

    @property
    def s3_client(self):
        if self.__s3_client__ is None:
            self.__s3_client__ = self.boto3_session.client('s3')
        return self.__s3_client__

    def get_source(self, environment, template):
        s3_object = self.s3_client.get_object(Bucket=self.bucket, Key=template)
        if not s3_object:
            return NotFoundError(f"No file '{template}' in bucket '{self.bucket}'")
        template_content = s3_object['Body'].read().decode('utf-8')

        def uptodate():
            return False
        return template_content, None, uptodate


class JinjaRenderMicroservice(TechMicroService):
    """ Render a jinja template to html
        Templates can be sent to the microservice in 3 differents ways :
            - send files in multipart/form-data body
            - put template content in url
            - put templates in a s3 bucket and give bucket name to the microservice """

    def post_render(self, template_name):
        """ render one template from templates given in multipart/form-data body
            pass jinja context in query_params """
        content_type = self.current_request.headers.get('content-type')
        multipart_decoder = decoder.MultipartDecoder(self.current_request.raw_body, content_type)
        templates = {}
        for part in multipart_decoder.parts:
            headers = {k.decode('utf-8'): v.decode('utf-8') for k, v in part.headers.items()}
            content = part.content.decode('utf-8')
            _, content_disposition_params = cgi.parse_header(headers['Content-Disposition'])
            filename = content_disposition_params['filename']
            templates[filename] = content
        context = self.current_request.query_params
        env = jinja2.Environment(loader=jinja2.DictLoader(templates))
        template = env.get_template(template_name)
        render = template.render(**context)
        response = Response(body=render,
                            status_code=200,
                            headers={'Content-Type': 'text/html'})
        return response

    def get_render_(self, template):
        """ render template which content is given in url
        pass jinja context in query_params """
        template = urllib.parse.unquote_plus(template)
        context = self.current_request.query_params
        env = jinja2.Environment(loader=jinja2.DictLoader({'index.html': template}))
        template = env.get_template('index.html')
        render = template.render(**context)
        response = Response(body=render,
                            status_code=200,
                            headers={'Content-Type': 'text/html'})
        return response

    def get_render__(self, bucket, template_name):
        """ render template stored on s3
        pass jinja context in query_params """
        bucket = urllib.parse.unquote_plus(bucket)
        template_name = urllib.parse.unquote_plus(template_name)
        context = self.current_request.query_params
        env = jinja2.Environment(loader=S3Loader(bucket))
        template = env.get_template(template_name)
        render = template.render(**context)
        response = Response(body=render,
                            status_code=200,
                            headers={'Content-Type': 'text/html'})
        return response
