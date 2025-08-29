from io import BytesIO
from unittest.mock import MagicMock
import pytest

from src.services.checksum_service import get_file_checksum

"""
Checksums from Python's standard hashlib library are likely correct but for
independence the expected sha256 values are taken from  https://sha256hash.org/
Except for empty string which it does not support but can get from Mac command line using
`echo -n "" | shasum -a 256` which gives:
"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
"""


def get_mock_upload_file(filename="testfile.txt", content="abc123"):
    file = MagicMock()
    file.filename = filename
    file.file = BytesIO(content.encode())
    return file


def test_get_file_checksum_single_example():
    mockfileobject = get_mock_upload_file(content="A")
    checksum, error = get_file_checksum(mockfileobject)
    assert checksum == "559aead08264d5795d3909718cdd05abd49572e84fe55590eef31a88a08fdffd"
    assert error == ""


def test_get_file_checksum_empty_string():
    mockfileobject = get_mock_upload_file(content="")
    checksum, error = get_file_checksum(mockfileobject)
    assert checksum == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert error == ""


checksum_examples = [
    ("We live on a placid island of ignorance in the midst of black seas of infinity",
     "8257869896c140152baad438bdda45153309c73de96db45aef46c5f55131683f"),
    ("Sauce for the moose is sauce for the panda",
     "df1715e5975e9cb9a7709448ad63535677e620368d65780b767672ce7fda9e01",),
    ("1234567890",
     "c775e7b757ede630cd0aa1113bd102661ab38829ca52a6422ab782862f268646")
]


@pytest.mark.parametrize("file_content,expected_result", checksum_examples)
def test_get_file_checksum_multiple_examples(file_content, expected_result):
    checksum, error = get_file_checksum(get_mock_upload_file(content=file_content))
    assert checksum == expected_result and error == ""


# Test deactivated by putting an "x" at start of name so pytest ingnores it.
# This creates 1GB of data and a noticeable pause when running locally.
# Might only want to run this one occasionally on demand.
def xtest_get_checksum_works_with_bigger_file():
    mock_file_object = get_mock_upload_file()
    mock_file_object.file = BytesIO(bytes(1024 ** 3))
    checksum, error = get_file_checksum(mock_file_object)
    assert checksum == "49bc20df15e412a64472421e13fe86ff1c5165e18b2afccf160d4dc19fe68a14"
    assert error == ""


def test_get_error_response_when_checksum_fails():

    class BadIoObject:
        def seek(self, x):
            pass

    mock_file_object = get_mock_upload_file(filename="doomed.txt")
    mock_file_object.file = BadIoObject()
    checksum, error = get_file_checksum(mock_file_object)
    assert checksum == ""
    # Full error message not compared because it contains a memory address that varies, e.g. "object at 0x1064423c0"
    assert error.startswith("Unexpected error getting sha256 checksum from file 'doomed.txt'")
    assert error.endswith("is not a file-like object in binary reading mode.")
