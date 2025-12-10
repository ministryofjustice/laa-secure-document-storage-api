from typing import Tuple, Iterable, Any
import csv
import re
import structlog
import codecs
from fastapi import UploadFile
from src.validation.file_validator import FileValidator


logger = structlog.get_logger()


class ScanCSV(FileValidator):
    def validate(self, file_object: UploadFile, delimiter: str = ",", **kwargs) -> Tuple[int, str]:
        """
        Scans CSV file for potentially malicious content

        :param file_object: should be a CSV file
        :param delimiter: delimiter used in CSV file - optional defaults to comma
        :return: status_code: int, detail: str
        """
        status_code = 200
        message = ""
        try:
            # csv.reader needs iterable that returns strings but FastAPI file_object.file
            # returns bytes. codecs.iterdecode conveniently converts the byte values to str
            # whilst retaining line-by-line iteration.
            csv_reader = csv.reader(codecs.iterdecode(file_object.file, 'utf-8'),
                                    delimiter=delimiter)
            for ri, csv_row in enumerate(csv_reader):
                status_code, message = check_row_values(csv_row)
                if status_code != 200:
                    message = f"Problem in {file_object.filename} row {ri} - {message}"
                    break
        except (csv.Error, UnicodeDecodeError) as csv_err:
            logger.error(f"ScanCSV unable to process {file_object.filename}: {str(csv_err)}")
            status_code = 400
            message = f"Unable to process {file_object.filename}. Is it a CSV file?"
        except Exception as exc_err:
            logger.error(f"Error checking file {file_object.filename}: {exc_err}")
            status_code = 500
            message = f"Unexpected error when processing {file_object.filename}"
        return status_code, message


def check_row_values(row_values: Iterable[Any]) -> Tuple[int, str]:
    """
    Intended to be used with data in lists from csv.reader, but
    is capable of working with any iterable.
    """
    # Need default return values because row_values could be empty (which is automatically safe)
    status_code = 200
    message = ""
    for item in row_values:
        status_code, message = check_item(str(item))
        if status_code != 200:
            break
    return status_code, message


def check_item(item: str) -> Tuple[int, str]:
    item_core = item.strip()
    # Checks based on CLA team's CSVUploadSerializerBase.create method
    if re.match(r'<[^>]+>', item_core):
        return 400, f"possible HTML tag(s) found in {item_core}"
    # Matches 'javascript' + any number of whitespace + colon, with case ignored
    if re.match(r'javascript\s*:', item_core, flags=re.IGNORECASE):
        return 400, f"suspected javascript URL found in: {item_core}"
    if item_core.startswith(("=", "@", "+", "-")):
        return 400, f"forbidden initial character found: {item_core[0]}"
    return 200, ""
