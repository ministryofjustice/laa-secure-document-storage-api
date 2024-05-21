import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_retrieve_file_missing_key(client):
    # Act
    response = client.get('/retrieve_file/')

    # Assert
    assert response.status_code == 400
    assert 'detail' in response.json()
    assert response.json()['detail'] == 'File key is missing'


def mock_get_item(service_id, file_key):
    raise Exception("An error occurred (ResourceNotFoundException) when calling the GetItem operation: Cannot do "
                    "operations on a non-existent table")


from botocore.exceptions import ClientError


@patch("src.services.s3_service.retrieveFileUrl")
def test_retrieve_file_exception(retrieveFileUrl_mock,client):
    # Arrange
    file_key = 'test-file-key'
    expected_error_message = ('The file test_file_key could not be found')
    retrieveFileUrl_mock.side_effect = Exception(f'The file {file_key} could not be found')
    # Act
    try:
        client.get(f'/retrieve_file?file_key={file_key}')
    except Exception as e:
        # Assert
        assert str(e) == expected_error_message

