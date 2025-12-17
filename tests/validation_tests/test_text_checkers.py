import pytest
from src.validation.text_checkers import (sql_injection_check,
                                          html_tag_check,
                                          javascript_url_check,
                                          excel_char_check)


@pytest.mark.parametrize("item", [
    "Robert'); DROP TABLE students;--",
    "DROP TABLE students;--",
    "1;DROP TABLE users",
    "1'; DROP TABLE users-- 1",
    "' OR 1=1 -- 1",
    "' OR '1'='1'",
    "'; EXEC sp_MSForEachTable 'DROP TABLE ?'; --"
    ])
def test_sql_injection_check_finds_suspicious_content(item):
    result = sql_injection_check.check(item)
    assert result == (400, f"{sql_injection_check.message}{item.strip()}")


@pytest.mark.parametrize("item", [
    "or 1 = 1",  # similar to suspicious one but no ' chars here
    "bunion sand snowdrop",  # contains 'union`, 'and', 'drop'
    ";",
    "O'Malley"  # Unmatched '
    ])
def test_sql_injection_check_passes_ordinary_content(item):
    result = sql_injection_check.check(item)
    assert result == (200, "")


@pytest.mark.parametrize("item", ["<boo>", "Carmela <script>alert(Malicious Business)</script>"])
def test_html_tag_check_finds_suspicious_content(item):
    result = html_tag_check.check(item)
    assert result == (400, f"{html_tag_check.message}{item.strip()}")


@pytest.mark.parametrize("item", ["1<2", ">>>>here!", "bobins<<"])
def test_html_tag_check_passes_ordinary_content(item):
    result = html_tag_check.check(item)
    assert result == (200, "")


@pytest.mark.parametrize("item", [" javascript  :"])
def test_javascript_url_check_finds_suspicious_content(item):
    result = javascript_url_check.check(item)
    assert result == (400, f"{javascript_url_check.message}{item.strip()}")


@pytest.mark.parametrize("item", [" lavascript  :"])
def test_javascript_url_check_passes_ordinary_content(item):
    result = javascript_url_check.check(item)
    assert result == (200, "")


@pytest.mark.parametrize("item", ["+", "-", "=", "@", "+123", " -153", " ==", " @justice"])
def test_excel_char_check_finds_suspicious_content(item):
    result = excel_char_check.check(item)
    assert result == (400, f"{excel_char_check.message}{item.strip()}")


@pytest.mark.parametrize("item", ["1+", "a-b", "1=1", "a@b"])
def test_excel_char_check_passes_ordinary_content(item):
    result = excel_char_check.check(item)
    assert result == (200, "")
