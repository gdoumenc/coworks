import csv
import io
import json

from ..coworks import TechMicroService


class CSVMicroService(TechMicroService):

    def post_format(self, content="", remove_rows=None, remove_columns=None, delimiter=','):
        """Format JSON list to CSV content."""
        remove_rows = remove_rows or []
        remove_columns = remove_columns or []

        # Ckecks parameters
        rows = json.loads(content)
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC, delimiter=delimiter)
        for index, row in enumerate(rows):
            if index not in remove_rows:
                line = [col for idx, col in enumerate(row.values()) if idx not in remove_columns]
                writer.writerow(line)

        return output.getvalue()
