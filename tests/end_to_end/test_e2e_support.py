import os
import io
import pytest
from unittest.mock import patch
from tests.end_to_end.e2e_support import TokenManager, UploadFileData, make_unique_name, get_file_data_for_request

"""
These test are for the support code used by e2e tests.
They don't test the SDS application itself.
"""


class MockResponse:
    def __init__(self, status_code, json_response):
        self.status_code = status_code
        self.json_response = json_response
        self.text = str(self.json)

    def json(self):
        return self.json_response


mock_token = {"token_type": 'Bearer',
              "expires_in": 3599,
              "ext_expires_in": 3599,
              "access_token": "The significant owl hoots in the night"}


@pytest.mark.e2e
@pytest.mark.parametrize("expected_file", ["Postman/test_file.md",
                                           "Postman/eicar.txt",
                                           "Postman/test_file.exe"])
def test_expected_test_data_files_are_present(expected_file):
    assert os.path.isfile(expected_file) is True


@pytest.mark.e2e
def test_token_manager_has_expected_initial_attributes():
    token_getter = TokenManager("test_id", "test_secret", "https://fake_url")
    expected_params = {"client_id":  "test_id",
                       "client_secret": "test_secret",
                       "grant_type": "client_credentials",
                       "scope": "api://laa-sds-local/.default"}
    assert token_getter.params == expected_params
    assert token_getter.token_url == "https://fake_url"


@pytest.mark.e2e
def test_token_manager_gets_token():
    token_getter = TokenManager("test_id", "test_secret", "https://fake_url")
    # Note need to patch original name, not the "as client"
    with patch("httpx.post", return_value=MockResponse(200, mock_token)):
        token = token_getter.get_access_token()
    assert token == "The significant owl hoots in the night"


@pytest.mark.e2e
def test_token_manager_gets_headers():
    token_getter = TokenManager("test_id", "test_secret", "https://fake_url")
    # Note need to patch original name, not the "as client"
    with patch("httpx.post", return_value=MockResponse(200, mock_token)):
        headers = token_getter.get_headers()
    assert headers == {'Authorization': 'Bearer The significant owl hoots in the night'}


@pytest.mark.e2e
def test_upload_file_data_has_correct_initial_details():
    file_data = UploadFileData("Postman/test_file.md")
    assert file_data.file_details["file"][0] == "Postman/test_file.md"
    assert isinstance(file_data.file_details["file"][1], io.BufferedReader)
    assert file_data.file_details["file"][2] == "text/markdown"


@pytest.mark.e2e
def test_upload_file_data_has_correct_details_with_new_filename():
    file_data = UploadFileData("Postman/test_file.md", new_filename="newname.md")
    assert file_data.file_details["file"][0] == "newname.md"
    assert isinstance(file_data.file_details["file"][1], io.BufferedReader)
    assert file_data.file_details["file"][2] == "text/markdown"


@pytest.mark.e2e
def test_upload_file_data_file_read_can_be_reset():
    file_data = UploadFileData("Postman/test_file.md")
    reader = file_data.file_details["file"][1]
    _ = reader.read()
    old_tell = reader.tell()
    file_data.reset_seek()
    new_tell = reader.tell()
    assert old_tell > 0 and new_tell == 0


@pytest.mark.e2e
def test_upload_file_update_filename():
    file_data = UploadFileData("Postman/test_file.md")
    original_name = file_data.file_details["file"][0]
    file_data.update_filename("newname.md")
    assert file_data.file_details["file"][0] == "newname.md" != original_name


@pytest.mark.e2e
def test_upload_file_get_data_returns_expected_result():
    file_data = UploadFileData("Postman/test_file.md")
    reader = file_data.file_details["file"][1]
    _ = reader.read()
    file_data = file_data.get_data(new_filename="anothernewname.md")
    assert file_data["file"][0] == "anothernewname.md"
    assert file_data["file"][1].tell() == 0
    assert file_data["file"][2] == "text/markdown"


@pytest.mark.e2e
def test_make_unique_name():
    # Set comprehension. As set only contains unique items, len
    # should match range value if unique values generated.
    unique_names = {make_unique_name("abc") for i in range(100)}
    assert len(unique_names) == 100


@pytest.mark.e2e
def test_get_file_data_for_request():
    file_data = get_file_data_for_request("Postman/test_file.md", "uploadname.md")
    assert file_data["file"][0] == "uploadname.md"
    assert isinstance(file_data["file"][1], io.BufferedReader)
    assert file_data["file"][2] == "text/markdown"
