import json
import os

from coworks import Blueprint
from pygsheets import Worksheet, DataRange
from pygsheets import authorize, WorksheetNotFound


class GoogleSheets(Blueprint):

    def __init__(self, client_id_var_name, private_key_var_name, private_key_id_var_name, **kwargs):
        super().__init__(**kwargs)
        self.client_id_var_name = client_id_var_name
        self.private_key_var_name = private_key_var_name
        self.private_key_id_var_name = private_key_id_var_name
        self.google_client = None

        @self.before_first_activation
        def load_crendentials(event, context):
            client_id = os.getenv(self.client_id_var_name)
            if not client_id:
                raise EnvironmentError(f'{self.client_id_var_name} not defined in environment.')
            private_key = os.getenv(self.private_key_var_name)
            if not private_key:
                raise EnvironmentError(f'{self.private_key_var_name} not defined in environment.')
            private_key_id = os.getenv(self.private_key_id_var_name)
            if not private_key_id:
                raise EnvironmentError(f'{self.private_key_id_var_name} not defined in environment.')

            self.CREDENTIALS = {
                "type": "service_account",
                "project_id": "glassy-bonsai-277705",
                "private_key_id": private_key_id,
                "private_key": private_key,
                "client_email": "google-sheet-micro-service@glassy-bonsai-277705.iam.gserviceaccount.com",
                "client_id": client_id,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/google-sheet-micro-service%40glassy-bonsai-277705.iam.gserviceaccount.com"
            }

            os.environ['SERVICE_ACCOUNT_CREDENTIALS'] = json.dumps(self.CREDENTIALS)
            self.google_client = authorize(service_account_env_var="SERVICE_ACCOUNT_CREDENTIALS")

    def get_worksheets(self, key: str):
        """Get list of worksheet index and titles.
        :param key:         Document google key.
        """
        spreadsheet = self.google_client.open_by_key(key=key)
        return [{'index': w.index, 'title': w.title} for w in spreadsheet.worksheets()]

    def get_worksheet_all(self, key: str, worksheet: str, property='index', **kwargs):
        """Get data from worksheet.
        :param key:         Document google key.
        :param worksheet:   Worksheet property.
        :param property:    May be index, title or id.
        """
        return self._get_worksheet(key, worksheet, property=property).get_all_records(**kwargs)

    def get_worksheet_value(self, key: str, worksheet: str, addr, property='index'):
        """Get data from worksheet.
        :param key:         Document google key.
        :param worksheet:   Worksheet property.
        :param property:    May be index, title or id.
        :param start:       Top left cell address. Can be unbounded.
        :param end:         Bottom right cell address.
        """
        return self._get_worksheet(key, worksheet, property=property).get_value(addr)

    def get_worksheet_values(self, key: str, worksheet: str, property='index', start=(1, 1), end=(1, None), **kwargs):
        """Get data from worksheet.
        :param key:         Document google key.
        :param worksheet:   Worksheet property.
        :param property:    May be index, title or id.
        :param start:       Top left cell address. Can be unbounded.
        :param end:         Bottom right cell address.
        """
        return self._get_worksheet(key, worksheet, property=property).get_values(start, end, **kwargs)

    def post_worksheet(self, key: str, index=0, title='', **kwargs):
        """Add a new worksheet.
        :param key:     Document google key.
        :param index:   Tab index of the worksheet.
        :param title:   Worksheet's title.
        """
        spreadsheet = self.google_client.open_by_key(key=key)
        spreadsheet.add_worksheet(title, index=index, **kwargs)

    def post_worksheet_content(self, key: str, worksheet: str, property='index', values=None, start=(1, 1), **kwargs):
        """Write data in worksheet.
        """
        worksheet = self._get_worksheet(key, worksheet, property=property)
        worksheet.update_values(start, values, **kwargs)

    def _get_worksheet(self, key, worksheet, *, property) -> Worksheet:
        spreadsheet = self.google_client.open_by_key(key=key)
        worksheet = spreadsheet.worksheet(property=property, value=worksheet)
        return worksheet
