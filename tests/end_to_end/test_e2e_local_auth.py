import os
from io import BytesIO
import httpx as client
import pytest
from tests.end_to_end.e2e_helpers import make_unique_name

"""
This file contains end-to-end tests that bypass usual authentication, so must have:
- Environment variable LOCAL_CONFIG_SKIP_AUTH="True"
- Request headers must include test-username value
- Only work with SDS application running locally (on 127.0.0.1)

Tests will be automatically skipped if the above environment variable is not set.
The skipping relies on pytestmark defined below.

Note the @pytest.mark.e2e decorator has a similar name but is is unrelated to the skipping,
it's just used to identify all pytest e2e tests regardless of authentication handling.
"""


# Module-level pytest global variable for test skipping. Tests in this file will be skipped
# when LOCAL_CONFIG_SKIP_AUTH environment variable != "True".
pytestmark = pytest.mark.skipif(os.getenv("LOCAL_CONFIG_SKIP_AUTH", "false").lower() != "true",
                                reason="bypass-auth not enabled")

# These tests are only expected to work when run locally
HOST_URL = "http://127.0.0.1:8000"


def make_file_details(content: bytes, filename: str = "test_file.txt", mimetype: str = "text/plain") -> dict:
    """
    Alternative way of providing file data - does not require files.
    Creates file content in RAM that works with HTTP clients: requests and httpx.
    Curiously, when posting using requests we can submit StringIO data but with httpx
    we must use BytesIO
    """
    return {"file": (filename, BytesIO(content), mimetype)}


def make_bulkload_file_details(content: bytes, filename: str = "test_file.txt", mimetype: str = "text/plain") -> tuple:
    """
    A curiosity of python http clients is they require file details to be in a dictionary format
    when uploading one file but in tuple format when loading more than one. This function
    returns the tuple version used when uploading multiple files. Note still one file per
    tuple, need to place the tuples in a list to load multiple files.
    """
    dict_version = make_file_details(content, filename, mimetype)
    return ("files", dict_version["file"])


def extract_bulk_load_success_count(response_status_code: int, response_json: str | list | dict) -> int:
    """
    Returns a count of the number of successful loads from a bulk_upload response.
    """
    success_count = 0
    if response_status_code == 200 and isinstance(response_json, dict):
        for _, file_details in response_json.items():
            outcomes = file_details.get("outcomes", [])
            if len(outcomes) == 1 and outcomes[0]["status_code"] in (200, 201):
                success_count += 1
    return success_count


# Get File

@pytest.mark.e2e
def test_get_file_succeeds_when_allowed_by_client_config():
    params = {"file_key": "README.md"}
    headers = {"test-username": "all-endpoint-local-test-user"}
    response = client.get(f"{HOST_URL}/get_file", headers=headers, params=params)
    assert response.status_code == 200
    assert "fileURL" in response.text
    assert "Expires" in response.text
    assert params["file_key"] in response.text


@pytest.mark.e2e
def test_get_file_fails_when_not_allowed_by_csv_client_config():
    params = {"file_key": "README.md"}
    headers = {"test-username": "virus-check-local-test-user"}
    response = client.get(f"{HOST_URL}/get_file", headers=headers, params=params)
    assert response.status_code == 403
    # Note the Forbidden message has " quotes within the string
    assert response.text == '"Forbidden"'


# Save/Update File

# Same operation with different users who have different permissions
@pytest.mark.e2e
@pytest.mark.parametrize("username,expected_code,expected_text_fragment", [
    ("all-endpoint-local-test-user", 201, "File saved successfully"),
    ("put-file-local-test-user", 415, "File extension not allowed"),
    ("virus-check-local-test-user", 403, "Forbidden")
    ])
def test_save_or_update_file_with_different_user_permissions(username, expected_code, expected_text_fragment):
    newfilename = make_unique_name("oh_no_its.xml")
    upload_file = make_file_details(b"borogoves", newfilename, "text/plain")
    response = client.put(f"{HOST_URL}/save_or_update_file",
                          headers={"test-username": username},
                          files=upload_file,
                          data={"body": '{"bucketName": "sds-local"}'})
    assert response.status_code == expected_code
    assert expected_text_fragment in response.text


@pytest.mark.e2e
@pytest.mark.parametrize("username,expected_code,expected_text_fragment", [
    ("all-endpoint-local-test-user", 201, "File saved successfully"),
    ("put-file-local-test-user", 415, "File extension not allowed"),
    ("virus-check-local-test-user", 403, "Forbidden")
    ])
def test_save_file_with_different_user_permissions(username, expected_code, expected_text_fragment):
    newfilename = make_unique_name("oh_no_its.xml")
    upload_file = make_file_details(b"borogoves", newfilename, "text/plain")
    response = client.post(f"{HOST_URL}/save_file",
                           headers={"test-username": username},
                           files=upload_file,
                           data={"body": '{"bucketName": "sds-local"}'})
    assert response.status_code == expected_code
    assert expected_text_fragment in response.text


@pytest.mark.e2e
@pytest.mark.parametrize("username,expected_code,expected_success_count", [
    ("all-endpoint-local-test-user", 200, 4),  # All files allowed
    ("put-file-local-test-user", 200, 3),  # One file blocked as xml blocked in user's json file
    ("virus-check-local-test-user", 403, 0)  # Load prevented as user lacks permission
    ])
def test_bulk_upload_with_different_user_permissions(username, expected_code, expected_success_count):

    files = [make_bulkload_file_details(b"Almery", "able.txt", "text/plain"),
             make_bulkload_file_details(b"Baslag", "baker.txt", "text/plain"),
             make_bulkload_file_details(b"Carcosa", "charly.txt", "text/plain"),
             make_bulkload_file_details(b"Drearbruh", "delta.xml", "text/plain")]

    response = client.put(f"{HOST_URL}/bulk_upload",
                          headers={"test-username": username},
                          files=files,
                          data={"body": '{"bucketName": "sds-local"}'})

    details = response.json()
    success_count = extract_bulk_load_success_count(response.status_code, details)

    assert response.status_code == expected_code
    assert success_count == expected_success_count


# Delete Files

@pytest.mark.e2e
@pytest.mark.parametrize("username,expected_code,expected_text_fragment", [
    ("all-endpoint-local-test-user", 200, "204"),  # User can save files and delete them
    ("put-file-local-test-user", 403, "Forbidden")  # User can save files but cannot delete
])
def test_delete_files_with_different_users(username, expected_code, expected_text_fragment):
    # Uploading a file so there is something to delete
    newfilename = make_unique_name("delete_or_not.txt")
    upload_file = make_file_details(b"stay or go", newfilename, "text/plain")
    upload_response = client.put(f"{HOST_URL}/save_or_update_file",
                                 headers={"test-username": "all-endpoint-local-test-user"},
                                 files=upload_file,
                                 data={"body": '{"bucketName": "sds-local"}'})
    assert upload_response.status_code in (200, 201)
    # Try to delete the same file
    delete_response = client.delete(f"{HOST_URL}/delete_files",
                                    headers={"test-username": username},
                                    params={"file_keys": [newfilename]})

    assert delete_response.status_code == expected_code
    assert expected_text_fragment in delete_response.text


# Virus Check

@pytest.mark.e2e
@pytest.mark.parametrize("username,expected_code,expected_text_fragment", [
    ("virus-check-local-test-user", 400, "Virus Found"),  # User can run virus check
    ("put-file-local-test-user", 403, "Forbidden")  # User can't run virus check
])
def test_virus_check_with_different_users(username, expected_code, expected_text_fragment):
    # Below creates eicar file content that triggers virus detection. Note the content needs to be at the
    # start of a file, so the bytes below should not cause the present pytest file to get flagged.
    # Using rb raw-bytes to avoid a warning about unescaped \P
    upload_file = make_file_details(rb"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*",
                                    "hmm.txt", "text/plain")
    response = client.put(f"{HOST_URL}/virus_check_file", headers={"test-username": username}, files=upload_file)
    assert response.status_code == expected_code
    assert expected_text_fragment in response.text


# Get File Details

@pytest.mark.e2e
@pytest.mark.parametrize("username,expected_code,expected_text_fragment", [
    ("all-endpoint-local-test-user", 200, "VersionId"),
    ("put-file-local-test-user", 403, "Forbidden")
])
def test_get_file_details_with_different_users(username, expected_code, expected_text_fragment):

    response = client.get(f"{HOST_URL}/get_file_details",
                          headers={"test-username": username},
                          params={"file_key": "README.md"})

    assert response.status_code == expected_code
    assert expected_text_fragment in response.text
