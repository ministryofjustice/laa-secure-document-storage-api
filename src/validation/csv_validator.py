from typing import Tuple, Iterable, Any
import structlog
from fastapi import UploadFile
from src.validation.file_validator import FileValidator


logger = structlog.get_logger()


class ScanCSV(FileValidator):
    def validate(self, file_object: UploadFile, delimiter: str = ",") -> Tuple[int, str]:
        status_code = 200
        message = ""
        try:
            for ri, row in enumerate(file_object.file):
                row_values = row.split(delimiter)
                status_code, message = check_row_values(row_values)
                if status_code != 200:
                    message = f"Problem in {file_object.filename} row {ri} - {message}"
                    break
        except AttributeError as atr_err:
            logger.error(f"Unable to process {file_object.filename}: {str(atr_err)}")
            status_code = 400
            message = f"Unable to process {file_object.filename}. Is it a CSV file?"
        except Exception as exc_err:
            logger.error(f"Error checking file {file_object.filename}: {str(exc_err)}")
            status_code = 500
            message = f"Unexpected error when processing {file_object.filename}"
        return status_code, message


def check_row_values(row_values: Iterable[Any]) -> Tuple[int, str]:
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
