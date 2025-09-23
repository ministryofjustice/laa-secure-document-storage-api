import pytest
# Using `as client`, so can easily switch between httpx and requests
import httpx as client
from tests.end_to_end.e2e_helpers import UploadFileData
from tests.end_to_end.e2e_helpers import get_token_maanger
from tests.end_to_end.e2e_helpers import get_host_url
from tests.end_to_end.e2e_helpers import get_upload_body
from tests.end_to_end.e2e_helpers import make_unique_name
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
token_getter = get_token_maanger()
s3_client = LocalS3()


@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown_test_files():
    """
    Pre-test setup and post-test teardown for tests within this module (file) only.
    Makes standard upload files available to each test and closes them afterwards.
    Code before the "yield" is executed before the tests.
    Code after the "yield" is exected after the last test.
    """
    global test_md_file, virus_file, disallowed_file
    test_md_file = UploadFileData("Postman/test_file.md")
    virus_file = UploadFileData("Postman/eicar.txt")
    disallowed_file = UploadFileData("Postman/test_file.exe")
    yield
    test_md_file.close_file()
    virus_file.close_file()
    disallowed_file.close_file()


new_filename = make_unique_name("save_path_file.txt")
paths = [f"{p}{new_filename}" for p in ("", "f1/", "f1/f2/")]


@pytest.mark.e2e
@pytest.mark.parametrize("new_filename", paths)
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
    assert s3_client.check_file_exists(new_filename) is True
