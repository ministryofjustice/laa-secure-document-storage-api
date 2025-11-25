import os
import pytest
# Using `as client`, so can easily switch between httpx and requests
import httpx as client
from tests.end_to_end.e2e_helpers import UploadFileData
from tests.end_to_end.e2e_helpers import get_token_manager
from tests.end_to_end.e2e_helpers import get_host_url
from tests.end_to_end.e2e_helpers import get_upload_body
from tests.end_to_end.e2e_helpers import make_unique_name
from tests.end_to_end.e2e_helpers import AuditDynamoDBClient

"""
This file is for e2e tests that require an actual SDS application to run against.
They all should be decorated with custom marker, @pytest.mark.e2e, to enable them
to be run separately from pytest unit tests.

* These tests mainly replicate our Postman tests but with a few differences *

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


if HOST_URL == "http://127.0.0.1:8000":
    audit_table_client = AuditDynamoDBClient(mocking_enabled=False)
else:
    audit_table_client = AuditDynamoDBClient(mocking_enabled=True)


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


@pytest.mark.e2e
def test_token_can_be_retrieved():
    "Establish that token retrieval is working"
    token_url = os.getenv('TOKEN_URL', token_getter.token_url)
    params = {'client_id': os.getenv('CLIENT_ID'),
              'client_secret': os.getenv('CLIENT_SECRET'),
              'scope': 'api://laa-sds-local/.default',
              'grant_type': 'client_credentials'
              }
    response = client.post(token_url, data=params)
    assert response.status_code == 200
    assert "Error" not in response.text


@pytest.mark.e2e
def test_no_token_when_invalid_scope_provided():
    "Alternative to Postman 'invalid scope token' test"
    invalid_scope = 'api://laa-sds-local/default'
    token_url = os.getenv('TOKEN_URL', token_getter.token_url)
    params = {'client_id': os.getenv('CLIENT_ID'),
              'client_secret': os.getenv('CLIENT_SECRET'),
              'scope': invalid_scope,
              'grant_type': 'client_credentials'
              }
    response = client.post(token_url, data=params)
    assert response.status_code == 400
    assert f"The provided value for scope {invalid_scope} is not valid" in response.text

# Health and Status Tests


@pytest.mark.e2e
def test_healthcheck_returns_expected_response():
    response = client.get(f"{HOST_URL}/health")
    assert response.status_code == 200
    assert response.text == '{"Health":"OK"}'


@pytest.mark.e2e
def test_ping_returns_expected_response():
    response = client.get(f"{HOST_URL}/ping")
    assert response.status_code == 200
    assert response.text == '{"ping":"pong"}'


@pytest.mark.e2e
def test_status_check_returns_expected_response():
    response = client.get(f"{HOST_URL}/status")
    status_dict = response.json()
    service_results = status_dict.get("services", [])
    sorted_labels = sorted([sr.get("label") for sr in service_results])

    bad_results = []
    for result in service_results:
        bad_results = bad_results + [r for r in result.get("observations", []) if r.get("category") != "success"]

    assert response.status_code == 200
    assert sorted_labels == ['antivirus', 'audit', 'authentication', 'authorisation', 'configuration', 'storage']
    assert bad_results == []


@pytest.mark.e2e
def test_available_validators_returns_expected_response():
    response = client.get(f"{HOST_URL}/available_validators")
    results = response.json()
    bad_results = []
    for result in results:
        if sorted(result.keys()) != ['description', 'name', 'validator_kwargs']:
            bad_results.append(result)
    assert response.status_code == 200
    assert bad_results == []

# Docs Test


@pytest.mark.e2e
def test_swagger_doc_is_available():
    response = client.get(f"{HOST_URL}/docs")
    assert response.status_code == 200
    assert "LAA Secure Document Storage API - Swagger UI" in response.text

# Auth Tests


@pytest.mark.e2e
def test_retrieve_file_unsuccessful_if_no_token():
    params = {"file_key": "README.md"}
    response = client.get(f"{HOST_URL}/retrieve_file", headers={}, params=params)
    assert response.status_code == 403
    assert response.text == '"Forbidden"'


@pytest.mark.e2e
def test_retrieve_file_unsuccessful_if_invalid_token():
    params = {"file_key": "README.md"}
    response = client.get(f"{HOST_URL}/retrieve_file",
                          headers={'Authorization': "Bearer bewarer"},
                          params=params)
    assert response.status_code == 401
    assert "Invalid or expired token" in response.text

# Save or Update File Tests


@pytest.mark.e2e
def test_put_new_file_once():
    new_filename = make_unique_name("put_new_file_test.txt")
    upload_file = test_md_file.get_data(new_filename)

    response = client.put(f"{HOST_URL}/save_or_update_file",
                          headers=token_getter.get_headers(),
                          files=upload_file,
                          data=UPLOAD_BODY)

    details = response.json()
    assert response.status_code == 201
    assert details["success"].startswith("File saved successfully")
    assert details["success"].endswith(f"with key {new_filename}")
    assert details["checksum"] == "718546961bb3d07169b89bc75c8775b605239bc7189ea0fb92eefc233228804a"


@pytest.mark.e2e
def test_put_new_file_twice_gives_expected_code_and_message():
    new_filename = make_unique_name("loaded_twice.txt")
    upload_file = test_md_file.get_data(new_filename)

    response1 = client.put(f"{HOST_URL}/save_or_update_file",
                           headers=token_getter.get_headers(),
                           files=upload_file,
                           data=UPLOAD_BODY)

    # This resets the "seek" position to start of file, to prevent 0-byte upload
    upload_file = test_md_file.get_data(new_filename)

    response2 = client.put(f"{HOST_URL}/save_or_update_file",
                           headers=token_getter.get_headers(),
                           files=upload_file,
                           data=UPLOAD_BODY)

    assert response1.status_code == 201 and str(response1.text).startswith('{"success":"File saved successfully')
    assert response2.status_code == 200 and str(response2.text).startswith('{"success":"File updated successfully')
    # Note other CREATE/UPDATE audit table checks are in test_e2e_file_and_folder.py
    if audit_table_client.mocking_enabled is False:
        audit_item1 = audit_table_client.get_audit_row_e2e(response1, 0)
        audit_item2 = audit_table_client.get_audit_row_e2e(response2, 0)
        assert audit_item1.get("file_id") == {'S': new_filename}
        assert audit_item1.get("operation_type") == {'S': 'CREATE'}
        assert audit_item1.get("error_details") == {'S': ''}
        assert audit_item2.get("file_id") == {'S': new_filename}
        assert audit_item2.get("operation_type") == {'S': 'UPDATE'}
        assert audit_item2.get("error_details") == {'S': ''}


@pytest.mark.e2e
def test_put_file_with_virus_is_blocked():
    upload_virus_file = virus_file.get_data()
    response = client.put(f"{HOST_URL}/save_or_update_file",
                          headers=token_getter.get_headers(),
                          files=upload_virus_file,
                          data=UPLOAD_BODY)
    assert response.status_code == 400
    assert response.json()["detail"] == ["Virus Found"]


@pytest.mark.e2e
def test_put_file_with_disallowed_file_type_is_blocked():
    upload_disallowed_file = disallowed_file.get_data()
    response = client.put(f"{HOST_URL}/save_or_update_file",
                          headers=token_getter.get_headers(),
                          files=upload_disallowed_file,
                          data=UPLOAD_BODY)
    assert response.status_code == 415
    assert response.json()["detail"] == "File mimetype not allowed"


@pytest.mark.e2e
def test_put_file_with_missing_bucket_is_blocked():
    new_filename = make_unique_name("put_new_file_test.txt")
    upload_file = test_md_file.get_data(new_filename)
    # Care with formatting the below - value needs to be str, delimted with '
    # (Although this is just creating a body that lacks bucketName)
    data = {"body": '{"folder": "testmult"}'}
    response = client.put(f"{HOST_URL}/save_or_update_file",
                          headers=token_getter.get_headers(),
                          files=upload_file,
                          data=data)
    assert response.status_code == 400
    assert response.json()["detail"]["bucketName"] == "Field required"


@pytest.mark.e2e
def test_put_file_without_file_fails_as_expected():
    response = client.put(f"{HOST_URL}/save_or_update_file",
                          headers=token_getter.get_headers(),
                          data=UPLOAD_BODY)
    assert response.status_code == 400
    assert response.json()["detail"] == ["File is required"]


# Retrieve File Tests (Deprecated)


@pytest.mark.e2e
def test_retrieve_file_is_successful():
    params = {"file_key": "README.md"}
    headers = token_getter.get_headers()
    response = client.get(f"{HOST_URL}/retrieve_file", headers=headers, params=params)
    assert response.status_code == 200
    assert "fileURL" in response.text
    assert "Expires" in response.text
    assert params["file_key"] in response.text


@pytest.mark.e2e
def test_retrieve_file_returns_expected_error_when_file_not_found():
    params = {"file_key": "does-not-exist.txt"}
    headers = token_getter.get_headers()
    response = client.get(f"{HOST_URL}/retrieve_file", headers=headers, params=params)
    assert response.status_code == 404
    assert "The file does-not-exist.txt could not be found." in response.text

# Get File Tests


@pytest.mark.e2e
def test_get_file_is_successful():
    params = {"file_key": "README.md"}
    headers = token_getter.get_headers()
    response = client.get(f"{HOST_URL}/get_file", headers=headers, params=params)
    assert response.status_code == 200
    assert "fileURL" in response.text
    assert "Expires" in response.text
    assert params["file_key"] in response.text


@pytest.mark.e2e
def test_get_file_returns_expected_error_when_file_not_found():
    expected_error = "The file does-not-exist.txt could not be found."
    params = {"file_key": "does-not-exist.txt"}
    headers = token_getter.get_headers()
    response = client.get(f"{HOST_URL}/get_file", headers=headers, params=params)
    assert response.status_code == 404
    assert expected_error in response.text
    # Note other READ audit table checks are in test_e2e_file_and_folder.py
    if audit_table_client.mocking_enabled is False:
        audit_item = audit_table_client.get_audit_row_e2e(response, 0)
        assert audit_item.get("file_id") == {'S': "does-not-exist.txt"}
        assert audit_item.get("operation_type") == {'S': 'FAILED'}
        assert audit_item.get("error_details") == {'S': f"{response.url}: {expected_error}"}

# Save File Tests


@pytest.mark.e2e
def test_post_new_file_once_is_successful():
    new_filename = make_unique_name("post_new_file_test.txt")
    upload_file = test_md_file.get_data(new_filename)

    response = client.post(f"{HOST_URL}/save_file",
                           headers=token_getter.get_headers(),
                           files=upload_file,
                           data=UPLOAD_BODY)

    details = response.json()
    assert response.status_code == 201
    assert details["success"].startswith("File saved successfully")
    assert details["success"].endswith(f"with key {new_filename}")
    assert details["checksum"] == "718546961bb3d07169b89bc75c8775b605239bc7189ea0fb92eefc233228804a"


@pytest.mark.e2e
def test_post_new_file_second_time_fails():
    new_filename = make_unique_name("post_new_file_test.txt")
    upload_file = test_md_file.get_data(new_filename)

    response1 = client.post(f"{HOST_URL}/save_file",
                            headers=token_getter.get_headers(),
                            files=upload_file,
                            data=UPLOAD_BODY)

    response2 = client.post(f"{HOST_URL}/save_file",
                            headers=token_getter.get_headers(),
                            files=upload_file,
                            data=UPLOAD_BODY)

    assert response1.status_code == 201
    assert str(response1.text).startswith('{"success":"File saved successfully')
    assert response2.status_code == 409
    assert str(response2.text).startswith(f'{{"detail":"File {new_filename} already exists and cannot be overwritten')


@pytest.mark.e2e
def test_post_file_with_virus_is_blocked():
    upload_virus_file = virus_file.get_data()
    response = client.post(f"{HOST_URL}/save_file",
                           headers=token_getter.get_headers(),
                           files=upload_virus_file,
                           data=UPLOAD_BODY)
    assert response.status_code == 400
    assert response.json()["detail"] == ["Virus Found"]


@pytest.mark.e2e
def test_post_file_with_disallowed_file_type_is_blocked():
    upload_disallowed_file = disallowed_file.get_data()
    response = client.post(f"{HOST_URL}/save_file",
                           headers=token_getter.get_headers(),
                           files=upload_disallowed_file,
                           data=UPLOAD_BODY)
    assert response.status_code == 415
    assert response.json()["detail"] == "File mimetype not allowed"


@pytest.mark.e2e
def test_post_file_with_missing_bucket_is_blocked():
    new_filename = make_unique_name("post_new_file_test.txt")
    upload_file = test_md_file.get_data(new_filename)
    # Care with formatting the below - value needs to be str, delimted with '
    # (Although this is just creating a body that lacks bucketName)
    data = {"body": '{"folder": "testmult"}'}
    response = client.post(f"{HOST_URL}/save_file", headers=token_getter.get_headers(), files=upload_file, data=data)
    assert response.status_code == 400
    assert response.json()["detail"]["bucketName"] == "Field required"


@pytest.mark.e2e
def test_post_file_without_file_fails_as_expected():
    response = client.post(f"{HOST_URL}/save_file", headers=token_getter.get_headers(), data=UPLOAD_BODY)
    assert response.status_code == 400
    assert response.json()["detail"] == ["File is required"]


# Virus Check Tests


@pytest.mark.e2e
def test_virus_check_detects_virus():
    upload_virus_file = virus_file.get_data()
    response = client.put(f"{HOST_URL}/virus_check_file", headers=token_getter.get_headers(), files=upload_virus_file)
    assert response.status_code == 400
    assert response.json()["detail"] == ["Virus Found"]


@pytest.mark.e2e
def test_virus_check_passes_clean_file():
    upload_file = test_md_file.get_data()
    response = client.put(f"{HOST_URL}/virus_check_file", headers=token_getter.get_headers(), files=upload_file)
    assert response.status_code == 200
    assert response.json()["success"] == "No virus found"
