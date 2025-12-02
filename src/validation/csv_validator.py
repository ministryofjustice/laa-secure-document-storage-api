from typing import Tuple, Iterable, Any
import csv
import structlog
from fastapi import UploadFile
from src.validation.file_validator import FileValidator


logger = structlog.get_logger()


class ScanCSV(FileValidator):
    def validate(self, file_object: UploadFile, delimiter: str = ",") -> Tuple[int, str]:
        status_code = 200
        message = ""
        try:
            csv_reader = csv.reader(file_object.file, delimiter=delimiter)
            for ri, csv_row in enumerate(csv_reader):
                status_code, message = check_row_values(csv_row)
                if status_code != 200:
                    message = f"Problem in {file_object.filename} row {ri} - {message}"
                    break
        except csv.Error as csv_err:
            logger.error(f"ScanCSV unable to process {file_object.filename}: {str(csv_err)}")
            status_code = 400
            message = f"Unable to process {file_object.filename}. Is it a CSV file?"
        except Exception as exc_err:
            logger.error(f"Error checking file {file_object.filename}: {exc_err}")
            status_code = 500
            message = f"Unexpected error when processing {file_object.filename}: {exc_err}"

        return status_code, message


def check_row_values(row_values: Iterable[Any]) -> Tuple[int, str]:
    # need default values because row_values could be empty (which is automatically safe)
    status_code = 200
    message = ""
    for item in row_values:
        status_code, message = check_item(str(item))
        if status_code != 200:
            break
    return status_code, message


def check_item(item: str) -> Tuple[int, str]:
    status_code = 200
    message = ""
    if item.strip() == "":
        # Empty is safe!
        return status_code, message
    # Checks based on CLA team's CSVUploadSerializerBase.create method
    if item.strip().startswith(("=", "@", "+", "-")):
        return 400, f"forbidden initial character found: {item.strip()[0]}."
    return status_code, message
