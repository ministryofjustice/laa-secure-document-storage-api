import pytest
from fastapi import UploadFile
from src.validation.csv_validator import check_item, check_row_values


def make_uploadfile(file_content, filename="dummy_file.txt", mime_type="text/plain"):
    headers = {
                'content-type': mime_type
            }
    return UploadFile(file=file_content, filename=filename, headers=headers)


@pytest.mark.parametrize("item", ["", "123", "1>2", ".@"])
def test_check_item_passes_allowed_items(item):
    result = check_item(item)
    assert result == (200, "")


@pytest.mark.parametrize("item,expected", [
    ("=", (400, "Invalid initial character found: =.")),
    (" =", (400, "Invalid initial character found: =.")),
    ("@", (400, "Invalid initial character found: @.")),
    (" @", (400, "Invalid initial character found: @.")),
    ("+", (400, "Invalid initial character found: +.")),
    (" +", (400, "Invalid initial character found: +.")),
    ("-", (400, "Invalid initial character found: -.")),
    (" -", (400, "Invalid initial character found: -."))
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
    [(1, 2, 3, "="), (400, "Invalid initial character found: =.")],
    [("=", 2, 3, 4), (400, "Invalid initial character found: =.")]
    ])
def test_check_row_values_with_bad_rows(row, expected):
    result = check_row_values(row)
    assert result == expected
