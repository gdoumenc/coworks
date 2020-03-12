import csv
import io
import json
from typing import Union, List

from ..coworks import TechMicroService


class CSVMicroService(TechMicroService):

    def post_format(self, content: str = "", title: Union[bool, List[str]] = True,
                    remove_rows: List[int] = None, remove_columns: List[int] = None,
                    delimiter: str = ','):
        """Format JSON list to CSV content."""

        remove_rows = remove_rows if remove_rows is not None else []
        remove_columns = remove_columns if remove_columns is not None else []
        if type(remove_rows) is not list:
            raise EnvironmentError("remove_rows parameter must be a list")
        if type(remove_columns) is not list:
            raise EnvironmentError("remove_columns parameter must be a list")

        rows = json.loads(content)
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

        return output.getvalue()
