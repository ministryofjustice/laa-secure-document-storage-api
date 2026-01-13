import pytest
from unittest.mock import patch, MagicMock
from src.validation.suspicious_content_validator import check_item, check_row_values, ScanForSuspiciousContent
from src.validation.text_checkers import text_checkers

from fastapi import UploadFile


checkers = text_checkers.values()


def make_uploadfile(file_content, filename="dummy_file.txt", mime_type="text/plain", to_bytes=True) -> UploadFile:
    """
    file_content potentially different formats, but for CSV content use a list of strings
    with one element per CSV row, e.g. ["1,2,3", "4,5,6", "7,8,9"] for 3-row file.
    Note although UploadFile capable of holding data as str or bytes, files uploaded are
    always delivered as bytes.
    """
    if to_bytes:
        file_content = [s.encode() for s in file_content]
    headers = {'content-type': mime_type}
    return UploadFile(file=file_content, filename=filename, headers=headers)


@pytest.mark.parametrize("item", ["", "123", "1>2", ".@", "<>", "havascript  :"])
def test_check_item_passes_allowed_items(item):
    result = check_item(item,  checkers=checkers)
    assert result == (200, "")


# check_item tests


@pytest.mark.parametrize("item,expected", [
    ("<Boo>", (400, "possible HTML tag(s) found in: <Boo>")),
    (" <Boo> ", (400, "possible HTML tag(s) found in: <Boo>")),
    ("Carmela <script>alert(Malicious Business)</script>",
     (400, "possible HTML tag(s) found in: Carmela <script>alert(Malicious Business)</script>")),
    ("<One><Two>", (400, "possible HTML tag(s) found in: <One><Two>")),
    (" javascript  :", (400, "suspected javascript URL found in: javascript  :")),
    (" JaVascriPT    :", (400, "suspected javascript URL found in: JaVascriPT    :")),
    ("=", (400, "forbidden initial character found: =")),
    (" =", (400, "forbidden initial character found: =")),
    ("@", (400, "forbidden initial character found: @")),
    (" @", (400, "forbidden initial character found: @")),
    ("+", (400, "forbidden initial character found: +")),
    (" +", (400, "forbidden initial character found: +")),
    ("-", (400, "forbidden initial character found: -")),
    (" -", (400, "forbidden initial character found: -"))
    ])
def test_check_item_finds_expected_issues(item, expected):
    result = check_item(item,  checkers=checkers)
    assert result == expected


@pytest.mark.parametrize("item", [
    "Robert'); DROP TABLE students;--",
    "DROP TABLE students;--",
    "1;DROP TABLE users",
    "1'; DROP TABLE users-- 1",
    "' OR 1=1 -- 1",
    "' OR '1'='1'",
    "'; EXEC sp_MSForEachTable 'DROP TABLE ?'; --"
    ])
def test_check_item_finds_possible_sql_injection(item):
    expected = (400, f"possible SQL injection found in: {item.strip()}")
    result = check_item(item, checkers=checkers)
    assert result == expected


@pytest.mark.parametrize("item", [
    "or 1 = 1",  # similar to suspicious one but no ' chars here
    "bunion sand snowdrop",  # contains 'union`, 'and', 'drop'
    ";",
    "O'Malley"  # Unmatched '
    ]
    )
def test_check_item_sql_injection_check_for_false_positives(item):
    result = check_item(item, checkers=checkers)
    assert result == (200, "")


# check_row_values tests


@pytest.mark.parametrize("good_row", [
    (1, 2, 3, 4, 5),
    ("1=", "2@", "3+", "4-"),
    (True, False, None),
    "thequickbrownfox"
    ])
def test_check_row_values_with_good_rows(good_row):
    result = check_row_values(good_row, checkers=checkers)
    assert result == (200, "")


@pytest.mark.parametrize("row,expected", [
    [(1, "<ha>", 3, 4), (400, "possible HTML tag(s) found in: <ha>")],
    [(1, 2, " javascript :", 4), (400, "suspected javascript URL found in: javascript :")],
    [(1, 2, 3, "="), (400, "forbidden initial character found: =")],
    [("=", 2, 3, 4), (400, "forbidden initial character found: =")],
    [("' OR '1'='1'", 2, 3, 4), (400, "possible SQL injection found in: ' OR '1'='1'")]
    ])
def test_check_row_values_with_bad_rows(row, expected):
    result = check_row_values(row, checkers=checkers)
    assert result == expected


@pytest.mark.parametrize("row,expected", [
    [("<a>", 2, 3, "="), (400, "possible HTML tag(s) found in: <a>")],
    [("=", 2, "<b>", 4), (400, "forbidden initial character found: =")]
    ])
def test_check_row_values_with_bad_rows_stops_at_first_problem(row, expected):
    result = check_row_values(row, checkers=checkers)
    assert result == expected


@pytest.mark.parametrize("row", [(1, "<ha>", 3, 4),
                                 (1, 2, " javascript :", 4),
                                 (1, 2, 3, "="),
                                 ("' OR '1'='1'", 2, 3, 4)])
def test_check_row_values_always_passes_when_checkers_empty(row):
    result = check_row_values(row, checkers=[])
    assert result == (200, "")


@pytest.mark.parametrize("row, expected", [
    [(1, "<ha>", 3, 4), (200, "")],
    [(1, 2, " javascript :", 4), (400, "suspected javascript URL found in: javascript :")],
    [(1, 2, 3, "="), (200, "")],
    [("' OR '1'='1'", 2, 3, 4), (200, "")]
    ])
def test_check_row_values_only_detects_issue_associated_with_supplied_checker(row, expected):
    result = check_row_values(row, checkers=[text_checkers.get("javascript_url_check")])
    assert result == expected


# Validator - tests with expected validation passes


@pytest.mark.parametrize("file_content", [
    [""],
    [","],
    [" , "],
    ["1,2,3,4,5,6"],
    ["1,2,3\n", "4,5,6\n", "7,8,9\n"],
    ["1 , 2, 3\n", "4, five, 6\n", "7, *, <\n"]
    ])
def test_scan_for_suspicious_content_passes_good_csv_files(file_content):
    file_object = make_uploadfile(file_content)
    validator = ScanForSuspiciousContent()
    result = validator.validate(file_object)
    assert result == (200, "")


@pytest.mark.parametrize("delimiter,file_content",
                         [(",", ["1,2,3", "4,5,6", "7,8,9"]),
                          (";", ["1;2;3", "4;5;6", "7;8;9"]),
                          ("#", ["1#2#3", "4#5#6", "7#8#9"])
                          ])
def test_scan_for_suspicious_content_works_with_different_csv_delimiters(delimiter, file_content):
    mock_scan = MagicMock(return_value=(200, ""))
    file_object = make_uploadfile(file_content, "variety.csv")
    validator = ScanForSuspiciousContent()
    with patch("src.validation.suspicious_content_validator.check_row_values", mock_scan):
        result = validator.validate(file_object, delimiter=delimiter)
    # Extract relevant part of mock's args_list into something more convenient
    # Interested in the values supplied, not the checkers
    wanted_args_list = [e[0][0] for e in mock_scan.call_args_list]
    assert result == (200, "")
    # Checking that the values have been correctly separated
    assert wanted_args_list == [['1', '2', '3'], ['4', '5', '6'], ['7', '8', '9'], ]


@pytest.mark.parametrize("file_content,expected", [
    (["1, 2, <zzz>\n", "4, 5, 6\n", "7, 8, 9"],
     (400,  "Problem in bad.csv row 0 - possible HTML tag(s) found in: <zzz>")),
    (["1, 2, 3\n", "4, 5, javascript  :\n", "7, 8, 9"],
     (400,  "Problem in bad.csv row 1 - suspected javascript URL found in: javascript  :")),
    (["1, 2, 3\n", "4, 5, 6\n", "7, 8, +9"],
     (400, "Problem in bad.csv row 2 - forbidden initial character found: +9"))
    ])
def test_scan_for_suspicious_content_finds_bad_csv_rows(file_content, expected):
    file_object = make_uploadfile(file_content, "bad.csv")
    validator = ScanForSuspiciousContent()
    result = validator.validate(file_object)
    assert result == expected


def test_scan_for_suspicious_content_passes_good_xml_file():
    file_content = ["<?xml version = '1.0' encoding = 'UTF-8'?>\n",
                    "<matterStart code=SCHEDULE_REF> 1234567890 </matterStart>"]
    file_object = make_uploadfile(file_content, "good.xml")
    validator = ScanForSuspiciousContent()
    result = validator.validate(file_object, xml_mode=True)
    assert result == (200, "")


# Validator - tests with expected validation failures


def test_scan_for_suspicious_content_finds_sql_injection_in_xml_file():
    file_content = ["<?xml version = '1.0' encoding = 'UTF-8'?>\n",
                    "<matterStart code=SCHEDULE_REF>Test' UNION SELECT * FROM users --</matterStart>"]
    file_object = make_uploadfile(file_content, "bad.xml")
    validator = ScanForSuspiciousContent()
    result = validator.validate(file_object, xml_mode=True)
    expected_message = ("Problem in bad.xml row 1 - possible SQL injection found in: "
                        "<matterStart code=SCHEDULE_REF>Test' UNION SELECT * FROM users --</matterStart>")
    assert result == (400, expected_message)


def test_scan_for_suspicious_content_with_invalid_file_data_gives_expected_error():
    "Not actual CSV data that can be checked"
    file_object = make_uploadfile([b"%PDF-1.4\r\n%\xe2\xe3\xcf\xd3\r\n"], "document.pdf", "application/pdf",
                                  to_bytes=False)
    validator = ScanForSuspiciousContent()
    result = validator.validate(file_object)
    assert result == (400, 'Unable to process document.pdf. Is it a valid file?')


def test_scan_for_suspicious_content_returns_expected_error_when_invalid_scan_types_given():
    file_object = make_uploadfile(["1,2,3"])
    validator = ScanForSuspiciousContent()
    result = validator.validate(file_object,
                                scan_types=["html_tag_check", "hidden_tiger_check", "crouching_dragon_check"])
    assert result == (400, "Invalid scan_types value(s) supplied: ['hidden_tiger_check', 'crouching_dragon_check']")


def test_scan_for_suspicious_content_runs_html_tag_check_in_xml_mode_if_manually_chosen():
    file_content = ["<?xml version = '1.0' encoding = 'UTF-8'?>\n",
                    "<matterStart code=SCHEDULE_REF> 1234567890 </matterStart>"]
    file_object = make_uploadfile(file_content, "good.xml")
    validator = ScanForSuspiciousContent()
    result = validator.validate(file_object, xml_mode=True, scan_types=["html_tag_check"])
    expected_message = ("Problem in good.xml row 0 - "
                        "possible HTML tag(s) found in: <?xml version = '1.0' encoding = 'UTF-8'?>")
    assert result == (400, expected_message)


# Validator - Checking that expected scans are included for default csv, default xml and for manual choice


def test_scan_for_suspicious_content_applies_expected_default_csv_scan_types():
    mock_scan = MagicMock(return_value=(200, ""))
    file_object = make_uploadfile(["1,2,3"])
    validator = ScanForSuspiciousContent()
    with patch("src.validation.suspicious_content_validator.check_row_values", mock_scan):
        result = validator.validate(file_object)
    # Mock should always return this but checking just in case
    assert result == (200, "")
    # Extract relevant part of mock's args_list into something more convenient
    # [0]on end because whole thing is in another list which only has one element
    checker_instance_list = [e[0][1] for e in mock_scan.call_args_list][0]
    checker_names = [e.name for e in checker_instance_list]
    assert checker_names == ['sql_injection_check', 'html_tag_check', 'javascript_url_check', 'excel_char_check']


def test_scan_for_suspicious_content_applies_expected_default_xml_scan_types():
    # 'html_tag_check' should be excluded from xml scan
    mock_scan = MagicMock(return_value=(200, ""))
    file_object = make_uploadfile(["1,2,3"])
    validator = ScanForSuspiciousContent()
    with patch("src.validation.suspicious_content_validator.check_row_values", mock_scan):
        result = validator.validate(file_object, xml_mode=True)
    assert result == (200, "")
    checker_instance_list = [e[0][1] for e in mock_scan.call_args_list][0]
    checker_names = [e.name for e in checker_instance_list]
    assert checker_names == ['sql_injection_check', 'javascript_url_check', 'excel_char_check']


@pytest.mark.parametrize("scan_types,expected_result", [
    (["sql_injection_check"], ["sql_injection_check"]),
    (["html_tag_check"], ["html_tag_check"]),
    # Same check requested twice but only executed once in result
    (["html_tag_check", "html_tag_check"], ["html_tag_check"]),
    # Two different checks - both executed
    (["sql_injection_check", "html_tag_check"], ["sql_injection_check", "html_tag_check"]),
    # Request order swapped wrt above, but execution order is unchanged as depends on definition in text_checkers.py
    (["html_tag_check", "sql_injection_check"], ["sql_injection_check", "html_tag_check"]),
    # Three checks (note line wrap to keep flake8 happy)
    (['sql_injection_check', 'html_tag_check', 'javascript_url_check'],
     ['sql_injection_check', 'html_tag_check', 'javascript_url_check'])
    ])
def test_scan_for_suspicious_content_runs_expected_manually_chosen_scans(scan_types, expected_result):
    mock_scan = MagicMock(return_value=(200, ""))
    file_object = make_uploadfile(["1,2,3"])
    validator = ScanForSuspiciousContent()
    with patch("src.validation.suspicious_content_validator.check_row_values", mock_scan):
        result = validator.validate(file_object, scan_types=scan_types)
    assert result == (200, "")
    checker_instance_list = [e[0][1] for e in mock_scan.call_args_list][0]
    checker_names = [e.name for e in checker_instance_list]
    assert checker_names == expected_result
