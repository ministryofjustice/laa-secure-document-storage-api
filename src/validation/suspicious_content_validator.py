from typing import Tuple, Iterable, Any, Iterator, TextIO
import csv
import structlog
import codecs
from fastapi import UploadFile
from src.validation.file_validator import FileValidator
from src.validation.text_checkers import text_checkers
from src.validation.text_checkers import StringCheck


logger = structlog.get_logger()


class ScanForSuspiciousContent(FileValidator):
    all_scan_types: list[str] = list(text_checkers.keys())
    xml_scan_types: list[str] = [e for e in all_scan_types if e != "html_tag_check"]

    def validate(self,
                 file_object: UploadFile,
                 delimiter: str = ",",
                 xml_mode: bool = False,
                 scan_types: Iterable[str] | None = None,
                 **kwargs) -> Tuple[int, str]:
        """
        Scans file for potentially malicious content

        :param file_object: should be a text file
        :param delimiter: delimiter used in CSV file - optional, defaults to comma
        :param xml_mode: xml file scan when true.
        :param scan_types: optional iterable of chosen scan types. All supplied values must be valid
                           otherwise the scan will return a 400 error. Defaults to all scan types if
                           xml_mode is False, but default excludes html_tag_check when xml_mode is True.
                           Note when manually specified, html_tag_check will run in xml_mode but will
                           almost certainly result in "fail" result because xml files typically include
                           tags. Also if scan_type is repeated, it will still only run once.
        :return: status_code: int, detail: str
        """
        status_code = 200
        message = ""

        if scan_types:
            invalid_scan_types = self.find_invalid_scan_types(scan_types)
            if invalid_scan_types:
                return 400, (f"Invalid scan_types value(s) supplied: {invalid_scan_types}."
                             f" Must be from: {self.all_scan_types}.")
        else:
            scan_types = self.all_scan_types
            if xml_mode:
                scan_types = self.xml_scan_types
        # each checker only included once even if listed more than once in scan_types
        checkers = [v for k, v in text_checkers.items() if k in scan_types]

        if xml_mode:
            reader = line_reader
        else:
            reader = csv.reader

        try:
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
            logger.error(f"ScanForMaliciousContent unable to process {file_object.filename}: "
                         f"{csv_err.__class__.__name__} {csv_err}")
            status_code = 400
            message = f"Unable to process {file_object.filename}. Is it a valid file?"
        except Exception as exc_err:
            logger.error(f"Error checking file {file_object.filename}: {exc_err.__class__.__name__} {exc_err}")
            status_code = 500
            message = f"Unexpected error when processing {file_object.filename}"
        return status_code, message

    def find_invalid_scan_types(self, scan_types: Iterable[str]) -> list[str]:
        return [st for st in scan_types if st not in self.all_scan_types]


def line_reader(file: TextIO, **kwargs) -> Iterator[list[str]]:
    "Does similar thing to csv.reader but for non-CSV files"
    for row in file:
        yield [row.strip()]


def check_row_values(row_values: Iterable[Any], checkers: list[StringCheck]) -> Tuple[int, str]:
    # Need default return values because row_values could be empty (which is automatically safe)
    status_code = 200
    message = ""
    for item in row_values:
        status_code, message = check_item(str(item), checkers)
        if status_code != 200:
            break
    return status_code, message


def check_item(item: str, checkers: list[StringCheck]) -> Tuple[int, str]:
    result = (200, "")
    for checker in checkers:
        result = checker.check(item)
        if result[0] != 200:
            break
    return result
