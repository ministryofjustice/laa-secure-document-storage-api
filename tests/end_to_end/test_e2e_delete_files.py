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

* These tests concern the delete_files endpoint. *

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
# otherwise s3_client.check_file_exists & s3_client.list_versions return mock values. 
# This is to save on having to set S3 credentials for every environment.
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


@pytest.mark.e2e
def test_delete_single_file_deletes_the_requested_file_only():
    headers = token_getter.get_headers()
    # Upload a file to be deleted
    unwanted_filename = make_unique_name("file_to_be_deleted.txt")
    unwanted_file_response = post_a_file(url=HOST_URL,
                                         headers=headers,
                                         file_data=test_md_file.get_data(unwanted_filename))
    # Upload a file to be left alone
    wanted_filename = make_unique_name("file_to_be_retained.txt")
    wanted_file_response = post_a_file(url=HOST_URL,
                                       headers=headers,
                                       file_data=test_md_file.get_data(wanted_filename))

    # Delete the file
    params = {"file_keys": [unwanted_filename]}
    del_response = client.delete(f"{HOST_URL}/delete_files", headers=headers, params=params)
    # Retreive the other file
    get_response = client.get(f"{HOST_URL}/get_file", headers=headers, params={"file_key": wanted_filename})
    # This is really checking a preparation steps
    assert unwanted_file_response.status_code == wanted_file_response.status_code == 201
    # Note response.status should always be 202 but can be other results for the individual files
    assert del_response.status_code == 202
    assert del_response.json().get(unwanted_filename) == 204
    assert get_response.status_code == 200


@pytest.mark.e2e
def test_file_cannot_be_retrieved_after_it_has_been_deleted():
    headers = token_getter.get_headers()
    # Upload a file to be deleted
    new_filename = make_unique_name("file_to_be_deleted.txt")
    _ = post_a_file(url=HOST_URL, headers=headers, file_data=test_md_file.get_data(new_filename))
    # Delete the file
    del_params = {"file_keys": [new_filename]}
    _ = client.delete(f"{HOST_URL}/delete_files", headers=headers, params=del_params)
    # Try to get the deleted file
    get_response = client.get(f"{HOST_URL}/get_file", headers=headers, params={"file_key": new_filename})
    assert get_response.status_code == 404
    assert f"The file {new_filename} could not be found." in get_response.text


@pytest.mark.e2e
def test_delete_file_with_no_file_key_fails_as_expected():
    response = client.delete(f"{HOST_URL}/delete_files", headers=token_getter.get_headers())
    assert response.status_code == 400
    assert response.json()["detail"] == "File key is missing"


@pytest.mark.e2e
def test_delete_file_without_authorisation_fails_as_expected():
    params = {"file_keys": ["should_not_matter_as_no_authorisation.txt"]}
    response = client.delete(f"{HOST_URL}/delete_files", headers={}, params=params)
    assert response.status_code == 403
    assert response.text == '"Forbidden"'


@pytest.mark.e2e
def test_delete_non_existent_file_fails_as_expected():
    params = {"file_keys": ["non_existent_file"]}
    response = client.delete(f"{HOST_URL}/delete_files", headers=token_getter.get_headers(), params=params)
    assert response.status_code == 202
    assert response.json() == {"non_existent_file": 404}

# Note the Postman tests have "Retrieve Deleted File" and "Retrieve Non-Deleted File" tests
# at this point. They have not been replicated here as they seem to just duplicate Retrieve File
# tests for non-existent and existent files.
# Although tests above test_delete_single_file_deletes_the_requested_file_only and
# test_file_cannot_be_retrieved_after_it_has_been_deleted have supplementary "gets"
# to check (a) delete did not affect unrelated file (b) file cannot be retrieved after deletion.


@pytest.mark.e2e
def test_delete_multiple_files_has_right_result_for_each_file():
    headers = token_getter.get_headers()
    # Upload 2 files to be deleted
    new_filename1 = make_unique_name("file_to_be_deleted.txt")
    new_filename2 = make_unique_name("another_file_to_be_deleted.txt")
    _ = post_a_file(url=HOST_URL, headers=headers, file_data=test_md_file.get_data(new_filename1))
    _ = post_a_file(url=HOST_URL, headers=headers, file_data=test_md_file.get_data(new_filename2))
    # Request deletion of two valid files and one non-existent file
    params = {"file_keys": [new_filename1, new_filename2, "non_existent_file"]}
    response = client.delete(f"{HOST_URL}/delete_files", headers=token_getter.get_headers(), params=params)
    assert response.status_code == 202
    assert response.json() == {new_filename1: 204, new_filename2: 204, "non_existent_file": 404}


@pytest.mark.e2e
def test_all_versions_of_file_are_deleted():
    headers = token_getter.get_headers()
    # Upload multiple versions of a file to be deleted
    new_filename = make_unique_name("file_to_be_deleted.txt")
    for _ in range(3):
        post_a_file(url=HOST_URL, headers=headers, file_data=test_md_file.get_data(new_filename))
    # Use global s3_client that adapts to environment to assert that all versions exist in bucket
    mock_versions = [f"{new_filename}_v{i}" for i in range(1, 4)]
    versions = s3_client.list_versions(new_filename, mock_keys=mock_versions if s3_client.mocking_enabled else None)
    assert len(versions) == 3, f"Expected 3 versions, but found {len(versions)}"
    # Call delete_files endpoint
    params = {"file_keys": [new_filename]}
    client.delete(f"{HOST_URL}/delete_files", headers=headers, params=params)
    # Check that all versions are deleted
    remaining_versions = s3_client.list_versions(new_filename, mock_keys=[new_filename] if s3_client.mocking_enabled else None)
    assert len(remaining_versions) == 0, f"Expected no versions, but found {len(remaining_versions)}"
