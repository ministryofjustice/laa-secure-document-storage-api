from unittest.mock import patch
from fastapi import HTTPException
from fastapi.testclient import TestClient
from src.main import app
from src.models.execeptions.file_not_found import FileNotFoundException

test_client = TestClient(app)


def test_retrieve_file_missing_key():
    # Act
    response = test_client.get('/retrieve_file/')

    # Assert
    assert response.status_code == 400
    assert 'detail' in response.json()
    assert response.json()['detail'] == 'File key is missing'


def mock_get_item(service_id, file_key):
    raise Exception("An error occurred (ResourceNotFoundException) when calling the GetItem operation: Cannot do "
                    "operations on a non-existent table")


@patch("src.services.s3_service.retrieveFileUrl")
def test_retrieve_file_not_found(retrieveFileUrl_mock):
    # Arrange
    file_key = 'test-file-key'
    expected_error_message = ('The file test_file_key could not be found')
    retrieveFileUrl_mock.side_effect = FileNotFoundException(f'The file {file_key} could not be found', file_key)
    # Act
    try:
        test_client.get(f'/retrieve_file?file_key={file_key}')
    except HTTPException as e:
        # Assert
        assert str(e.detail) == expected_error_message
        assert str(e.status_code) == '404'


@patch("src.services.s3_service.retrieveFileUrl")
def test_retrieve_unknown_exception(retrieveFileUrl_mock):
    file_key = 'test-file-key'
    retrieveFileUrl_mock.side_effect = Exception('unknown exception')
    try:
        test_client.get(f'/retrieve_file?file_key={file_key}')
    except HTTPException as e:
        assert str(e.detail) == 'An error occurred while retrieving the file'
        assert str(e.status_code) == '500'
