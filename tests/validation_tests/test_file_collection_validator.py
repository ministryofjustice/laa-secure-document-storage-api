import mimetypes
from fastapi import UploadFile
from src.validation.file_collection_validator import MaxFileCount, MinFileCount, MaxCombinedFileSize
from unittest.mock import AsyncMock
import pytest


def make_uploadfile(content: bytes = b"123", name: str = 'test.txt') -> UploadFile:
    """
    Helper to create an UploadFile object, optionally specifying content and filename.
    """
    file = AsyncMock(spec=UploadFile)
    file.read.return_value = content
    file.size = len(content)
    file.filename = name
    file.content_type = mimetypes.guess_type(name)[0]
    return file


def make_file_list(count: int) -> list[UploadFile]:
    test_file = make_uploadfile()
    return [test_file] * count


# Individual Validator - Maximum File Count

def test_max_file_count_with_too_many_files():
    five_files = make_file_list(5)
    validator = MaxFileCount()
    status_code, message = validator.validate(five_files, max_count=4)
    assert status_code == 422 and message == "Too many files. 5 submitted but maximum is 4."


@pytest.mark.parametrize("file_list,expected_status_code,expected_message", [
    (make_file_list(0), 200, ""),  # Zero files is unrealistic but included for completeness
    (make_file_list(1), 200, ""),
    (make_file_list(2), 200, ""),
    (make_file_list(3), 200, ""),
    (make_file_list(4), 422, "Too many files. 4 submitted but maximum is 3."),
    (make_file_list(5), 422, "Too many files. 5 submitted but maximum is 3."),
    (make_file_list(6), 422, "Too many files. 6 submitted but maximum is 3.")
    ])
def test_max_file_count_fixed_max_with_different_counts(file_list, expected_status_code, expected_message):
    validator = MaxFileCount()
    status_code, message = validator.validate(file_list, 3)
    assert status_code == expected_status_code and message == expected_message


@pytest.mark.parametrize("max_file_count,expected_status_code,expected_message", [
    (0, 422, "Too many files. 4 submitted but maximum is 0."),
    (1, 422, "Too many files. 4 submitted but maximum is 1."),
    (2, 422, "Too many files. 4 submitted but maximum is 2."),
    (3, 422, "Too many files. 4 submitted but maximum is 3."),
    (4, 200, ""),
    (5, 200, ""),
    ])
def test_max_file_count_fixed_file_count_with_different_limits(max_file_count, expected_status_code, expected_message):
    four_files = make_file_list(4)
    validator = MaxFileCount()
    status_code, message = validator.validate(four_files, max_file_count)
    assert status_code == expected_status_code and message == expected_message


# Individual Validator - Minimum File Count

@pytest.mark.parametrize("file_list,min_file_count,expected_status_code,expected_message", [
    (make_file_list(0), 0, 200, ""),
    (make_file_list(0), 1, 422, "Too few files. 0 submitted but minimum is 1."),
    (make_file_list(1), 1, 200, ""),
    (make_file_list(1), 2, 422, "Too few files. 1 submitted but minimum is 2."),
    (make_file_list(2), 2, 200, ""),
    (make_file_list(2), 3, 422, "Too few files. 2 submitted but minimum is 3."),
    (make_file_list(3), 3, 200, ""),
    (make_file_list(1), 100, 422, "Too few files. 1 submitted but minimum is 100."),
    (make_file_list(99), 100, 422, "Too few files. 99 submitted but minimum is 100."),
    (make_file_list(100), 100, 200, "")
    ])
def test_minimum_file_count(file_list, min_file_count, expected_status_code, expected_message):
    validator = MinFileCount()
    status_code, message = validator.validate(file_list, min_file_count)
    assert status_code == expected_status_code and message == expected_message


# Individual Validator - Maximum combined file size

def test_total_file_size_within_limit_4_files():
    "Four 1-byte files and limit of 4 bytes - pass"
    one_byte_file = make_uploadfile(b"A")
    file_list = [one_byte_file] * 4
    validator = MaxCombinedFileSize()
    status_code, message = validator.validate(file_list, max_combined_size=4)
    assert status_code == 200 and message == ""


@pytest.mark.parametrize("file_list,max_combined_size,expected_status_code,expected_message", [
    ([make_uploadfile("A")] * 1, 1, 200, ""),
    ([make_uploadfile("A")] * 2, 1, 422, "Combined file size 2 B exceeds limit of 1 B."),
    ([make_uploadfile("A")] * 2, 2, 200, ""),
    ([make_uploadfile("A")] * 3, 2, 422, "Combined file size 3 B exceeds limit of 2 B."),
    ([make_uploadfile("ABCD")] * 1, 4, 200, ""),
    ([make_uploadfile("AB")] * 2, 4, 200, ""),
    ([make_uploadfile("A")] * 4, 4, 200, ""),
    ([make_uploadfile("A")] * 5, 4, 422, "Combined file size 5 B exceeds limit of 4 B."),
    ([make_uploadfile("AB")] * 3, 4, 422, "Combined file size 6 B exceeds limit of 4 B."),
    ([make_uploadfile("AB")] * 3, 5, 422, "Combined file size 6 B exceeds limit of 5 B."),
    ([make_uploadfile("AB")] * 3, 6, 200, "")
    ])
def test_total_file_size(file_list, max_combined_size, expected_status_code, expected_message):
    validator = MaxCombinedFileSize()
    status_code, message = validator.validate(file_list, max_combined_size)
    assert status_code == expected_status_code and message == expected_message
