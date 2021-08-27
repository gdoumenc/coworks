import json

import requests

# from coworks.tech.csv import CSVMicroService

csv_content = json.dumps([
    {"col1": "value1", "col2": "value2"},
    {"col1": "value3", "col2": "value4"},
])


import pytest
@pytest.mark.skip
class ToBeRedoneTestCSV:

    def test_format(self, local_server_factory):
        local_server = local_server_factory(CSVMicroService())
        response = local_server.make_call(requests.post, '/format',
                                          json={'content': csv_content, 'title': False})
        assert response.status_code == 200
        assert response.text == '"value1","value2"\r\n"value3","value4"\r\n'
        response = local_server.make_call(requests.post, '/format',
                                          json={'content': csv_content})
        assert response.status_code == 200
        assert response.text == '"col1","col2"\r\n"value1","value2"\r\n"value3","value4"\r\n'
        response = local_server.make_call(requests.post, '/format',
                                          json={'content': csv_content, 'remove_rows': [0], 'remove_columns': [1]})
        assert response.status_code == 200
        assert response.text == '"col1"\r\n"value3"\r\n'
        response = local_server.make_call(requests.post, '/format',
                                          json={'content': csv_content, 'title': ['test1', 'test2']})
        assert response.status_code == 200
        assert response.text == '"test1","test2"\r\n"value1","value2"\r\n"value3","value4"\r\n'
        response = local_server.make_call(requests.post, '/format',
                                          json={'content': csv_content, 'delimiter': '\t'})
        assert response.status_code == 200
        assert response.text == '"col1"\t"col2"\r\n"value1"\t"value2"\r\n"value3"\t"value4"\r\n'
