import os
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.routers.retrieve_file import retrieve_file


@pytest.fixture
def client():
    return TestClient(app)


def test_retrieve_file_missing_key(client):
    # Act
    response = client.get('/retrieve_file/')

    # Assert
    assert response.status_code == 404
    assert 'detail' in response.json()
    assert response.json()['detail'] == 'Not Found'


def mock_get_item(service_id, file_key):
    raise Exception("An error occurred (ResourceNotFoundException) when calling the GetItem operation: Cannot do "
                    "operations on a non-existent table")


def test_retrieve_file_exception(client):
    # Arrange
    file_key = 'test-file-key'
    expected_error_message = ('An error occurred (ResourceNotFoundException) when calling the GetItem operation: '
                              'Cannot do operations on a non-existent table')
    os.environ['EQUINITI_SERVICE_ID'] = 'equiniti-service-id'

    # Act
    try:
        retrieve_file(file_key)
    except Exception as e:
        # Assert
        assert str(e) == expected_error_message
