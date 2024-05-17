import os
import pytest
from fastapi import HTTPException
from src.main import app
from fastapi.testclient import TestClient
from src.routers.retrieve_file import router
from src.services.Audit_Service import put_item
from src.services.s3_service import retrieveFileUrl
from src.utils.operation_types import OperationType


@pytest.fixture
def client():
    return TestClient(app)


@router.get('/retrieve_file/{file_key}')
async def retrieve_file(file_key: str = None):
    if file_key is None:
        raise HTTPException(status_code=400, detail="File key is missing")

    try:
        print(f"Retrieving file for key: {file_key}")
        put_item("equiniti-service-id", file_key, OperationType.READ)
        response = retrieveFileUrl(file_key)
        print(f"Retrieved file URL: {response}")
        return {'fileURL': response}
    except Exception as e:
        print(f"Error retrieving file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def test_retrieve_file_missing_key(client):
    # Act
    response = client.get('/retrieve_file/')

    # Assert
    assert response.status_code == 404
    assert 'detail' in response.json()
    assert response.json()['detail'] == 'Not Found'


def test_retrieve_file_exception(client):
    # Arrange
    file_key = 'test-file-key'
    expected_error_message = ('An error occurred (ResourceNotFoundException) when calling the GetItem operation: '
                              'Cannot do operations on a non-existent table')
    os.environ['EQUINITI_SERVICE_ID'] = 'equiniti-service-id'

    # Act
    response = client.get(f'/retrieve_file/{file_key}')

    # Assert
    assert response.status_code == 500
    assert response.json()['detail'] == expected_error_message
