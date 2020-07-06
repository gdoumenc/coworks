import json
import os
from urllib.parse import unquote_plus

import pygsheets
from chalice import Response
from pygsheets.exceptions import WorksheetNotFound

from coworks import TechMicroService


class GoogleSheetsMicroservice(TechMicroService):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.google_client = None

        @self.before_first_activation
        def load_crendentials():
            self.CREDENTIALS = {
                "type": "service_account",
                "project_id": "glassy-bonsai-277705",
                "private_key_id": os.getenv('PRIVATE_KEY_ID'),
                "private_key": os.getenv('PRIVATE_KEY'),
                "client_email": "google-sheet-micro-service@glassy-bonsai-277705.iam.gserviceaccount.com",
                "client_id": os.getenv('CLIENT_ID'),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/google-sheet-micro-service%40glassy-bonsai-277705.iam.gserviceaccount.com"
            }

            os.environ['SERVICE_ACCOUNT_CREDENTIALS'] = json.dumps(self.CREDENTIALS)
            self.google_client = pygsheets.authorize(service_account_env_var="SERVICE_ACCOUNT_CREDENTIALS")

    def get_worksheet(self, key: str, worksheet: str):
        """Get data from worksheet
        """
        spreadsheet = self.google_client.open_by_key(key=unquote_plus(key))
        worksheet = spreadsheet.worksheet_by_title(unquote_plus(worksheet))

        return Response(
            body=worksheet.get_all_records(),
            status_code=200,
            headers={'content-type': 'application/json'}
        )

    def post_worksheet(self):
        """Write data on worksheet"""
        request = self.current_request.json_body

        write_data_on_worksheet(
            key=request.get('key'),
            worksheet_title=request.get('worksheet'),
            data=request.get('data'),
            column_names=request.get('column_names'),
        )

        return Response(
            body={'success': True},
            status_code=200,
            headers={'content-type': 'application/json'}
        )

    def post_worksheets(self):
        """Write data on worksheets"""
        for request_element in self.current_request.json_body:
            write_data_on_worksheet(
                key=request_element.get('key'),
                worksheet_title=request_element.get('worksheet'),
                data=request_element.get('data'),
                column_names=request_element.get('column_names'),
            )

        return Response(
            body={'success': True},
            status_code=200,
            headers={'content-type': 'application/json'}
        )


def write_data_on_worksheet(key: str, worksheet_title: str, column_names: list, data: list):
    """Write data on worksheet
    :param key: Spreadsheet key
    :type key: str
    :param worksheet_title: Worksheet title
    :type worksheet_title: str
    :param column_names: Column names
    :type column_names: list
    :param data: Data
    :type data: list of list
    """
    spreadsheet = google_client.open_by_key(key=key)

    if worksheet_title:
        try:
            worksheet = spreadsheet.worksheet_by_title(worksheet_title)
        except WorksheetNotFound:
            worksheet = None
    else:
        worksheet = spreadsheet.sheet1
        worksheet_title = worksheet.title

    # delete this worksheet if exists
    if worksheet:
        spreadsheet.del_worksheet(worksheet)

    number_of_columns = len(column_names)
    number_of_lines = len(data) + 1

    worksheet = spreadsheet.add_worksheet(worksheet_title, rows=number_of_lines, cols=number_of_columns)

    worksheet.update_values('A1', [column_names])
    worksheet.update_values('A2', data)


app = GoogleSheetsMicroservice(ms_name="google-sheets")
