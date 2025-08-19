import os
import pytest
from dotenv import load_dotenv
# Using `as client`, so can easily switch between httpx and requests
import httpx as client
from tests.end_to_end.e2e_support import TokenManager, UploadFileData
from tests.end_to_end.e2e_support import read_postman_env_file
from tests.end_to_end.e2e_support import make_unique_name

"""
This file is for e2e tests that require an actual SDS application to run against.
They all should be decorated with custom marker @pytest.mark.e2e to enable them
to be run separately from pytest unit tests.

Manual test execution for e2e only or excluding e2e:
    `pipenv run pytest -m e2e` - to run e2e tests only
    `pipenv run pytest -m "not e2e"` - to exclude e2e tests from run.

Environment Variables
    CLIENT_ID - required
    CLIENT_SECRET - required
    HOST_URL - optional, defaults to http://127.0.0.1:8000
    TOKEN_URL - optional, defaults to value in Postman/SDSLocal.postman_environment.json file
"""


postman_env_details = read_postman_env_file()
postman_token_url = postman_env_details.get("AzureTokenUrl")

load_dotenv()
HOST_URL = os.getenv('HOST_URL', 'http://127.0.0.1:8000')
token_getter = TokenManager(client_id=os.getenv('CLIENT_ID'),
                            client_secret=os.getenv('CLIENT_SECRET'),
                            token_url=os.getenv('TOKEN_URL', postman_token_url)
                            )

test_md_file = UploadFileData("Postman/test_file.md")


@pytest.mark.e2e
def test_token_can_be_retrieved():
    token_url = os.getenv('TOKEN_URL', postman_token_url)
    params = {'client_id': os.getenv('CLIENT_ID'),
              'client_secret': os.getenv('CLIENT_SECRET'),
              'scope': 'api://laa-sds-local/.default',
              'grant_type': 'client_credentials'
              }
    response = client.post(token_url, data=params)
    assert response.status_code == 200
    assert "Error" not in response.text


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


@pytest.mark.e2e
def test_swagger_doc_is_available():
    response = client.get(f"{HOST_URL}/docs")
    assert response.status_code == 200
    assert "LAA Secure Document Storage API - Swagger UI" in response.text


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


@pytest.mark.e2e
def test_get_file_is_successful():
    params = {"file_key": "README.md"}
    headers = token_getter.get_headers()
    response = client.get(f"{HOST_URL}/retrieve_file", headers=headers, params=params)
    assert response.status_code == 200
    assert "fileURL" in response.text
    assert "Expires" in response.text
    assert params["file_key"] in response.text


@pytest.mark.e2e
def test_put_new_file_once():
    upload_bucket = '{"bucketName": "sds-local"}'

    new_filename = make_unique_name("put_new_file_test.txt")
    upload_file = test_md_file.get_data(new_filename)

    response = client.put(f"{HOST_URL}/save_or_update_file",
                          headers=token_getter.get_headers(),
                          files=upload_file,
                          data={"body": upload_bucket})

    assert response.status_code == 201
    assert str(response.text).startswith('{"success":"File saved successfully')
    assert str(response.text).endswith(f'with key {new_filename}"}}')


@pytest.mark.e2e
def test_put_new_file_twice_gives_expected_code_and_message():
    upload_bucket = '{"bucketName": "sds-local"}'
    new_filename = make_unique_name("loaded_twice.txt")
    upload_file = test_md_file.get_data(new_filename)

    response1 = client.put(f"{HOST_URL}/save_or_update_file",
                           headers=token_getter.get_headers(),
                           files=upload_file,
                           data={"body": upload_bucket})

    # This resets the "seek" position to start of file, to prevent 0-byte upload
    upload_file = test_md_file.get_data(new_filename)

    response2 = client.put(f"{HOST_URL}/save_or_update_file",
                           headers=token_getter.get_headers(),
                           files=upload_file,
                           data={"body": upload_bucket})

    assert response1.status_code == 201 and str(response1.text).startswith('{"success":"File saved successfully')
    assert response2.status_code == 200 and str(response2.text).startswith('{"success":"File updated successfully')
