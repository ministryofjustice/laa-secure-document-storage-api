from typing import Tuple, Iterable, Any
import csv
import re
import structlog
import codecs
from typing import Iterator, TextIO
from fastapi import UploadFile
from src.validation.file_validator import FileValidator


logger = structlog.get_logger()


content_checkers = [
    # SQL Injection - uses two patterns separated by | character
    # Background info:
    # https://dsdmoj.atlassian.net/wiki/spaces/SDS/pages/5991596033/SQL+Injection+Detection+Experiment
    {
        "function": re.search,
        "pattern": r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION)\b|\bOR\s+1=1\b|\bOR\s+'1'='1'",
        "message": "possible SQL injection found in: ",
    },
    #  HTML Tags
    {
        "function": re.search,
        "pattern": r"<[^>]+>",
        "message": "possible HTML tag(s) found in: ",
    },
    # Javascript URL
    {
        "function": re.search,
        "pattern": r"javascript\s*:",
        "message": "suspected javascript URL found in: ",
    },
    # Starts with Excel special character (not using re here)
    {
        "function": lambda substring, string, **kwargs: string.startswith(substring),
        "pattern": ("=", "@", "+", "-"),
        "message": "forbidden initial character found: ",
    },
]


class ScanCSV(FileValidator):
    def validate(self, file_object: UploadFile, delimiter: str = ",", **kwargs) -> Tuple[int, str]:
        """
        Scans CSV file for potentially malicious content

        :param file_object: should be a text file
        :param delimiter: delimiter used in CSV file - optional defaults to comma
        :return: status_code: int, detail: str
        """
        status_code = 200
        message = ""
        try:
            if file_object.filename.lower().endswith(".xml"):
                reader = line_reader
                checkers = content_checkers[:1]
            else:
                reader = csv.reader
                checkers = content_checkers

            # reader needs iterable that returns strings but FastAPI file_object.file
            # returns bytes. codecs.iterdecode conveniently converts the byte values to str
            # whilst retaining line-by-line iteration.
            row_reader = reader(codecs.iterdecode(file_object.file, 'utf-8'), delimiter=delimiter)
            for ri, row in enumerate(row_reader):
                status_code, message = check_row_values(row, checkers)
                if status_code != 200:
                    message = f"Problem in {file_object.filename} row {ri} - {message}"
                    break
        except (csv.Error, UnicodeDecodeError) as csv_err:
            logger.error(f"ScanCSV unable to process {file_object.filename}: {csv_err.__class__.__name__} {csv_err}")
            status_code = 400
            message = f"Unable to process {file_object.filename}. Is it a valid file?"
        except Exception as exc_err:
            logger.error(f"Error checking file {file_object.filename}: {exc_err.__class__.__name__} {exc_err}")
            status_code = 500
            message = f"Unexpected error when processing {file_object.filename}"
        return status_code, message


def line_reader(file: TextIO, **kwargs) -> Iterator[list[str]]:
    "Does similar thing to csv.reader but for non-CSV files"
    for row in file:
        yield [row.strip()]


def check_row_values(row_values: Iterable[Any], checkers: list[dict] = content_checkers) -> Tuple[int, str]:
    """
    Intended to be used with data in lists from csv.reader, but
    is capable of working with any iterable.
    """
    # Need default return values because row_values could be empty (which is automatically safe)
    status_code = 200
    message = ""
    for item in row_values:
        status_code, message = check_item(str(item), checkers)
        if status_code != 200:
            break
    return status_code, message


def check_item(item: str, checkers: list[dict] = content_checkers) -> Tuple[int, str]:
    item_core = item.strip()
    for checker in checkers:
        if checker["function"](checker["pattern"], item_core, flags=re.IGNORECASE):
            return 400, checker["message"] + str(item_core)
    return 200, ""
