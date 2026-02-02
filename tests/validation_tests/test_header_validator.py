import pytest
from src.validation.header_validator import HaveContentLengthInHeaders, run_header_validators


def test_have_content_length_in_headers_passes_when_content_length_present():
    headers = {"content-length": 1}
    validator = HaveContentLengthInHeaders()
    result = validator.validate(headers)
    assert result == (200, "")


@pytest.mark.parametrize("bad_headers", [{}, {"content-length": None}])
def test_have_content_length_in_headers_fails_when_content_length_absent(bad_headers):
    validator = HaveContentLengthInHeaders()
    result = validator.validate(bad_headers)
    assert result == (411, "content-length header not found")


def test_header_validator_passess_good_header():
    result = run_header_validators({"content-length": 1})
    assert result == (200, "")


def test_header_validator_fails_bad_header():
    result = run_header_validators({})
    assert result == (411, "content-length header not found")
