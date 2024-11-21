from fastapi import UploadFile
from io import BufferedReader
from unittest.mock import AsyncMock
import pytest
import os


@pytest.fixture()
def get_file() -> BufferedReader:
    test_file_path = os.path.join(
        os.getcwd(), "tests/testFiles/ss-poc-test.txt")
    file = open(test_file_path, "rb")
    return file


@pytest.fixture()
def get_upload_file_request(get_file) -> bytes:
    file = get_file
    return {"file": ("ss-poc-test.txt", file)}


@pytest.fixture()
def get_default_mock_file():
    test_file = AsyncMock(spec=UploadFile)
    test_file.read.return_value = b'test_file_content'
    test_file.size = 1234
    test_file.filename = 'test.txt'
    test_file.content_type = 'text/plain'
    return test_file
