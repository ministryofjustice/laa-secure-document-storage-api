from io import BytesIO
import time
import pytest
# Using `as client`, so can easily switch between httpx and requests
import httpx as client
from tests.end_to_end.e2e_helpers import UploadFileData
from tests.end_to_end.e2e_helpers import get_token_manager
from tests.end_to_end.e2e_helpers import get_host_url
from tests.end_to_end.e2e_helpers import get_upload_body
from tests.end_to_end.e2e_helpers import make_unique_name
from tests.end_to_end.e2e_helpers import post_a_file
from tests.end_to_end.e2e_helpers import LocalS3

"""
This file is for e2e tests that require an actual SDS application to run against.
They all should be decorated with custom marker, @pytest.mark.e2e, to enable them
to be run separately from pytest unit tests.

* These tests mainly concern different types of file or folder. *

Manual test execution for e2e only or excluding e2e:
    `pipenv run pytest -m e2e` - to run e2e tests only
    `pipenv run pytest -m "not e2e"` - to exclude e2e tests from run.

Environment Variables
    CLIENT_ID - required
    CLIENT_SECRET - required
    HOST_URL - optional, defaults to http://127.0.0.1:8000
    TOKEN_URL - optional, defaults to value in Postman/SDSLocal.postman_environment.json file
"""


HOST_URL = get_host_url()
UPLOAD_BODY = get_upload_body()
token_getter = get_token_manager()
# Set to return genuine S3 responses when HOST is local ("http://127.0.0.1:8000")
# otherwise s3_client.check_file_exists returns a mock value. This is to save on
# having to set S3 credentials for every environment.
if HOST_URL == "http://127.0.0.1:8000":
    s3_client = LocalS3(mocking_enabled=False)
else:
    s3_client = LocalS3(mocking_enabled=True)


@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown_test_files():
    """
    Pre-test setup and post-test teardown for tests within this module (file) only.
    Makes standard upload files available to each test and closes them afterwards.
    Code before the "yield" is executed before the tests.
    Code after the "yield" is exected after the last test.
    """
    global test_md_file
    test_md_file = UploadFileData("Postman/test_file.md")
    yield
    test_md_file.close_file()


new_base_filename_post = make_unique_name("save_path_file.txt")
post_paths = [f"{p}{new_base_filename_post}" for p in ("", "f1/", "f1/f2/", "f1/f2/f3/")]


@pytest.mark.e2e
@pytest.mark.parametrize("new_filename", post_paths)
def test_post_file_paths_works_as_expected(new_filename):
    upload_file = test_md_file.get_data(new_filename)

    response = client.post(f"{HOST_URL}/save_file",
                           headers=token_getter.get_headers(),
                           files=upload_file,
                           data=UPLOAD_BODY)

    details = response.json()
    assert response.status_code == 201
    assert details["success"].startswith("File saved successfully")
    assert details["success"].endswith(f"with key {new_filename}")
    assert s3_client.check_file_exists(new_filename, mock_result=True) is True


new_base_filename_get = make_unique_name("get_path_file.txt")
get_paths = [f"{p}{new_base_filename_get}" for p in ("", "f1/", "f1/f2/", "f1/f2/f3/")]


@pytest.mark.e2e
@pytest.mark.parametrize("new_filename", get_paths)
def test_get_file_paths_works_as_expected(new_filename):
    headers = token_getter.get_headers()
    # Upload file to S3 so it's available to be retrieved
    _ = post_a_file(url=HOST_URL, headers=headers, file_data=test_md_file.get_data(new_filename))
    # Get the file using SDS API (this gives URL to file, not the actual content)
    get_response = client.get(f"{HOST_URL}/get_file", headers=headers, params={"file_key": new_filename})
    # Asserts
    assert get_response.status_code == 200
    assert "fileURL" in get_response.text
    assert "Expires" in get_response.text
    assert new_filename in get_response.text


@pytest.mark.e2e
def test_retrieved_file_has_expected_content():
    new_filename = make_unique_name("check_file_content.txt")
    headers = token_getter.get_headers()

    # Make fake file object with specific content (created in RAM to avoid saving actual file)
    # content data - upload needs bytes but assert at end needs str
    fake_file_content = f"Test file content: {time.time()}"
    fake_file = BytesIO(fake_file_content.encode("utf-8"))

    # Upload file to S3 so it's available to be retrieved
    files = {'file': (new_filename, fake_file, 'text/plain')}
    _ = post_a_file(url=HOST_URL, headers=headers, file_data=files)

    # Get the file download URL using SDS API
    get_response = client.get(f"{HOST_URL}/get_file", headers=headers, params={"file_key": new_filename})
    json_data = get_response.json()
    file_url = json_data.get("fileURL")

    # Bodge for pipeline run. Returned urls in pipeline are for 'localstack' but this can't be
    # accessed from here. Changing to 127.0.0.1 which does work. Note local-run urls are already
    # http://127.0.0.1
    if file_url.startswith("http://localstack"):
        file_url = "http://127.0.0.1" + file_url[17:]

    # Download the actual file content using URL extracted from SDS response
    download_response = client.get(file_url)

    # Check downloaded file content matches original
    assert get_response.status_code == 200
    assert download_response.text == fake_file_content


@pytest.mark.e2e
@pytest.mark.parametrize("new_filename", [" . ", "---.txt", "!!!!!.pdf", "😍.txt",
                                          "ɐnbᴉlɐ.ɐ", "和製漢語.. ", "a.لإطلاق", "🐵🙈🙉.😍"])
def test_put_unusual_but_valid_filename_is_accepted(new_filename):
    upload_file = test_md_file.get_data(new_filename)

    response = client.put(f"{HOST_URL}/save_or_update_file",
                          headers=token_getter.get_headers(),
                          files=upload_file,
                          data=UPLOAD_BODY)

    details = response.json()
    assert response.status_code in (200, 201)
    assert details["success"].endswith(f"with key {new_filename}")
    assert s3_client.check_file_exists(new_filename, mock_result=True) is True


@pytest.mark.e2e
@pytest.mark.parametrize("new_filename", [".", ".  ", "...", "a.", ".txt", "/", "//////", "/.txt"])
def test_put_invalid_filename_is_rejected(new_filename):
    "This test pre-dates mandatory file validators and was created for client-configured validators"
    upload_file = test_md_file.get_data(new_filename)

    response = client.put(f"{HOST_URL}/save_or_update_file",
                          headers=token_getter.get_headers(),
                          files=upload_file,
                          data=UPLOAD_BODY)

    assert response.status_code == 415
    assert s3_client.check_file_exists(new_filename, mock_result=False) is False


@pytest.mark.e2e
@pytest.mark.parametrize("new_filename", ["https://abc.com", "http://oldabc.com"])
def test_put_filename_with_url_is_rejected(new_filename):
    upload_file = test_md_file.get_data(new_filename)

    response = client.put(f"{HOST_URL}/save_or_update_file",
                          headers=token_getter.get_headers(),
                          files=upload_file,
                          data=UPLOAD_BODY)

    details = response.json()

    assert response.status_code == 400
    assert details["detail"] == "Filename must not contain URLs or web addresses"
    assert s3_client.check_file_exists(new_filename, mock_result=False) is False


@pytest.mark.e2e
@pytest.mark.parametrize("new_filename", [r"\12.txt", r"1\2.txt", "12\\.txt", r"12.\\txt", "12.txt\\"])
def test_put_filename_with_backslash_is_rejected(new_filename):
    upload_file = test_md_file.get_data(new_filename)

    response = client.put(f"{HOST_URL}/save_or_update_file",
                          headers=token_getter.get_headers(),
                          files=upload_file,
                          data=UPLOAD_BODY)

    details = response.json()

    assert response.status_code == 400
    assert details["detail"] == "Filename must not contain Windows-style directory path separators"
    assert s3_client.check_file_exists(new_filename, mock_result=False) is False


@pytest.mark.e2e
@pytest.mark.parametrize("new_filename,expected_message", [
    (f"abc{chr(27)}.pdf", "Filename contains control characters"),
    (f"abc{chr(127)}.doc", "Filename contains control characters"),
    ("abc¾.doc", "Filename contains non-printable characters"),
    ("«abc».doc", "Filename contains non-printable characters"),
    ("abc*.doc", "Filename contains characters that are not allowed"),
    ("abc?.doc", "Filename contains characters that are not allowed"),
    ("abc:.doc", "Filename contains characters that are not allowed")
    ])
def test_put_filename_with_unacceptable_chars_is_rejected(new_filename, expected_message):
    upload_file = test_md_file.get_data(new_filename)

    response = client.put(f"{HOST_URL}/save_or_update_file",
                          headers=token_getter.get_headers(),
                          files=upload_file,
                          data=UPLOAD_BODY)

    details = response.json()

    assert response.status_code == 400
    assert details["detail"] == expected_message
    assert s3_client.check_file_exists(new_filename, mock_result=False) is False


@pytest.mark.e2e
def test_zero_byte_file_can_be_uploaded():
    """
    Minimum allowed file size depends on optional client-configured validator
    MinFileSize. This test relies on this validator either being absent from
    laa-sds-client-local config or set to allow 0-byte files.
    """
    # Make fake file object that's empty (created in RAM to avoid saving actual file)
    new_filename = make_unique_name("empty_file.txt")
    fake_file = BytesIO(b"")
    files = {'file': (new_filename, fake_file, 'text/plain')}
    # Upload the file
    response = client.put(f"{HOST_URL}/save_or_update_file",
                          headers=token_getter.get_headers(),
                          files=files,
                          data=UPLOAD_BODY)
    assert response.status_code == 201
