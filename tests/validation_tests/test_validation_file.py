import pytest
from validation.validator import validate_request
from unittest.mock import MagicMock
from fastapi import UploadFile

class MockUploadFile:
    """Using mock file object because content_type attribute of fastapi UploadFile is inconveniently read-only"""
    def __init__(self, filename, size, content_type):
        self.filename = filename
        self.size = size
        self.content_type = content_type

def test_expected_fail_for_no_content_length_header():
    mocked_file = MagicMock()
    mocked_file.read = MagicMock(return_value=b'test_file_content')
    # Create a mock for UploadFile
    mocked_upload_file = MagicMock(spec=UploadFile)
    mocked_upload_file.filename = 'test.xlsx'
    mocked_upload_file.content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    mocked_upload_file.file = mocked_file  # Assign the file mock to 'file' attribute
    mocked_upload_file.size = 1234
    test_header = {}
    result = validate_request(test_header, mocked_upload_file)
    assert result.status_code == 411 and result.message == ["content-length header not found"]

def test_expected_fail_for_no_file_received():
    test_file = None
    test_header = {'content-length': 1}
    result = validate_request(test_header, test_file)
    assert result.status_code == 400 and result.message == ["No file received"]


@pytest.mark.parametrize("filesize,contentlength", [(0, 1), (1, 2)])
def test_expected_success_for_content_length_bigger_than_file_size(filesize, contentlength):
    # test_file = MockUploadFile("test.xlsx", filesize,
                            #    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    test_file = MagicMock(spec = UploadFile)
    test_file.size = filesize
    mocked_file = MagicMock()
    mocked_file.read = MagicMock(return_value=b'test_file_content')
    test_file.file = mocked_file
    test_header = {'content-length': contentlength}
    result = validate_request(test_header, test_file)
    assert result.status_code == 200 and result.message == []


def test_expected_fail_for_file_too_long():
    # test_file = MockUploadFile("test.xlsx", 2000001,
    #                            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    # test_header = {'content-length': 2000002}
    test_file = MagicMock(spec = UploadFile)
    test_file.size = 2000001
    mocked_file = MagicMock()
    mocked_file.read = MagicMock(return_value=b'test_file_content')
    test_file.file = mocked_file
    test_header = {'content-length': 2000002}
    result = validate_request(test_header, test_file)
    assert result.status_code == 413 and result.message == ["File size suspiciously large (over 2000000 bytes)"]
