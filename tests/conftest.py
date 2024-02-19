from io import BufferedReader
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
