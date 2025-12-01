from typing import Tuple, Iterable, Any
from fastapi import UploadFile
from src.validation.file_validator import FileValidator


class CSVScan(FileValidator):
    def validate(self, file_object: UploadFile, delimiter: str = ",") -> Tuple[int, str]:
        try:
            for ri, row in enumerate(file_object.file):
                row_values = row.split(delimiter)
                status_code, message = check_row_values(row_values)
                if status_code != 200:
                    message = message + f" In row {ri}."
                    break

        except UnicodeDecodeError as ude_err:
            message = f"{ude_err}"

        except Exception as exc_err:
            message = f"{exc_err}"


def check_row_values(row_values: Iterable[Any]) -> Tuple[int, str]:
    for item in row_values:
        status_code, message = check_item(str(item))
        print(item,  status_code, message)
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
        return 400, f"Invalid initial character found: {item.strip()[0]}."
    return status_code, message
