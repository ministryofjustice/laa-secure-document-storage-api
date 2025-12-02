import pytest
from src.validation.csv_validator import check_item, check_row_values, ScanCSV

from fastapi import UploadFile


def make_uploadfile(file_content, filename="dummy_file.txt", mime_type="text/plain") -> UploadFile:
    """
    file_content potentially different formats but for CSV content, use a list of strings
    with one element per CSV row, e.g. ["1,2,3", "4,5,6", "7,8,9"] for 3-row file.
    """
    headers = {
        'content-type': mime_type
        }
    return UploadFile(file=file_content, filename=filename, headers=headers)


@pytest.mark.parametrize("item", ["", "123", "1>2", ".@"])
def test_check_item_passes_allowed_items(item):
    result = check_item(item)
    assert result == (200, "")


@pytest.mark.parametrize("item,expected", [
    ("=", (400, "forbidden initial character found: =.")),
    (" =", (400, "forbidden initial character found: =.")),
    ("@", (400, "forbidden initial character found: @.")),
    (" @", (400, "forbidden initial character found: @.")),
    ("+", (400, "forbidden initial character found: +.")),
    (" +", (400, "forbidden initial character found: +.")),
    ("-", (400, "forbidden initial character found: -.")),
    (" -", (400, "forbidden initial character found: -."))
    ]
                         )
def test_check_item_finds_expected_issues(item, expected):
    result = check_item(item)
    assert result == expected


@pytest.mark.parametrize("good_row", [
    (1, 2, 3, 4, 5),
    ("1=", "2@", "3+", "4-"),
    (True, False, None),
    "thequickbrownfox"
    ])
def test_check_row_values_with_good_rows(good_row):
    result = check_row_values(good_row)
    assert result == (200, "")


@pytest.mark.parametrize("row,expected", [
    [(1, 2, 3, "="), (400, "forbidden initial character found: =.")],
    [("=", 2, 3, 4), (400, "forbidden initial character found: =.")]
    ])
def test_check_row_values_with_bad_rows(row, expected):
    result = check_row_values(row)
    assert result == expected


@pytest.mark.parametrize("file_content", [
    [""],
    [","],
    [" , "],
    ["1,2,3,4,5,6"],
    ["1,2,3\n", "4,5,6\n", "7,8,9\n"]
    ])
def test_csv_scan_passes_good_files(file_content):
    file_object = make_uploadfile(file_content)
    validator = ScanCSV()
    result = validator.validate(file_object)
    assert result == (200, "")


def test_csv_scan_finds_bad_row():
    file_object = make_uploadfile(["1, 2, 3\n", "4, =5, 6\n", "7, 8, 9"], "bad.csv")
    validator = ScanCSV()
    result = validator.validate(file_object)
    assert result == (400, "Problem in bad.csv row 1 - forbidden initial character found: =.")


def test_csv_scan_finds_another_bad_row():
    file_object = make_uploadfile(["1, 2, 3\n", "4, 5, 6\n", "7, 8, +9"], "also_bad.csv")
    validator = ScanCSV()
    result = validator.validate(file_object)
    assert result == (400, "Problem in also_bad.csv row 2 - forbidden initial character found: +.")


def test_csv_scan_with_invalid_file_data_gives_expecte_error():
    "Not actual CSV data that can be checked"
    file_object = make_uploadfile(b"%PDF-1.4\r\n%\xe2\xe3\xcf\xd3\r\n19", "document.pdf", "application/pdf")
    validator = ScanCSV()
    result = validator.validate(file_object)
    assert result == (400, 'Unable to process document.pdf. Is it a CSV file?')
