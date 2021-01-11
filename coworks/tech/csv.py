import csv
import io
import json
from datetime import datetime
from typing import Union, List

from ..coworks import TechMicroService
from ..coworks import aws


class CSVMicroService(TechMicroService, aws.Boto3Mixin):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.aws_s3_session = aws.AwsS3Session()

    def upload_to_s3(self, file_obj, bucket, expiration=3600):
        """ Upload a file to s3 and return a presigned url to download it """
        try:
            response = self.aws_s3_session.client.upload_fileobj(
                file_obj, bucket, file_obj.name, ExtraArgs={'ContentType': 'text/csv'})
        except Exception as e:
            print(e)
        try:
            response = self.aws_s3_session.client.generate_presigned_url(
                'get_object', Params={'Bucket': bucket, 'Key': file_obj.name}, ExpiresIn=expiration)
            return response
        except Exception as e:
            print(e)

    def post_format(self, content: str = "", title: Union[bool, List[str]] = True,
                    remove_rows: List[int] = None, remove_columns: List[int] = None,
                    delimiter: str = ',', upload_to_s3_bucket: str = None, s3_bucket_folder: str = None):
        """Format JSON list to CSV content."""

        remove_rows = remove_rows if remove_rows is not None else []
        remove_columns = remove_columns if remove_columns is not None else []
        if type(remove_rows) is not list:
            raise EnvironmentError("remove_rows parameter must be a list")
        if type(remove_columns) is not list:
            raise EnvironmentError("remove_columns parameter must be a list")

        rows = json.loads(content) if type(content) == str else content
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC, delimiter=delimiter)

        if title is True:  # takes title from keys of first line
            line = [key for idx, key in enumerate(rows[0]) if idx not in remove_columns]
            writer.writerow(line)
        elif type(title) is list:
            line = [col for idx, col in enumerate(title) if idx not in remove_columns]
            writer.writerow(line)
        for index, row in enumerate(rows):
            if index not in remove_rows:
                line = [col for idx, col in enumerate(row.values()) if idx not in remove_columns]
                writer.writerow(line)

        res = output.getvalue()

        if upload_to_s3_bucket:
            file_obj = io.BytesIO(res.encode('utf-8'))
            if s3_bucket_folder:
                file_obj.name = f"{s3_bucket_folder}/{datetime.now()}.csv"
            else:
                file_obj.name = f"{datetime.now()}.csv"
            return self.upload_to_s3(file_obj, upload_to_s3_bucket)
        else:
            return res
