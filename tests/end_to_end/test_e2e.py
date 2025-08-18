import os
import pytest
from dotenv import load_dotenv
# Using `as client`, so can easily switch between httpx and requests
import httpx as client
from tests.end_to_end.e2e_support import TokenManager


"""
This file is for e2e tests that require an actual SDS application to run against.
They all should be decorated with custom marker @pytest.mark.e2e to enable them
to be run separately from pytest unit tests.

Manual test execution:
`pipenv run pytest -m e2e` to run e2e tests only
`pipenv run pytest -m "not e2e"` to exclude e2e tests from run.
"""

load_dotenv()
HOST_URL = os.getenv('host_url', 'http://localhost:8000')
token_getter = TokenManager(client_id=os.getenv('client_id'),
                            client_secret=os.getenv('client_secret'),
                            token_url=os.getenv('token_url')
                            )


@pytest.mark.e2e
def test_healthcheck_returns_expected_response():
    response = client.get(f"{HOST_URL}/health")
    assert response.status_code == 200
    assert response.text == '{"Health":"OK"}'


@pytest.mark.e2e
def test_swagger_doc_is_available():
    response = client.get(f"{HOST_URL}/docs")
    assert response.status_code == 200
    assert "LAA Secure Document Storage API - Swagger UI" in response.text


@pytest.mark.e2e
def test_get_file_is_successful():
    params = {"file_key": "README.md"}
    headers = token_getter.get_headers()
    response = client.get(f"{HOST_URL}/retrieve_file", headers=headers, params=params)
    assert response.status_code == 200
    assert "fileURL" in response.text
    assert "Expires" in response.text
    assert params["file_key"] in response.text
