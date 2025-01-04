from unittest.mock import patch

from src.models.execeptions.file_not_found import FileNotFoundException


def test_retrieve_file_missing_key(test_client):
    response = test_client.get('/retrieve_file/')

    assert response.status_code == 400
    assert 'detail' in response.json()
    assert response.json()['detail'] == 'File key is missing'


def mock_get_item(service_id, file_key):
    raise Exception("An error occurred (ResourceNotFoundException) when calling the GetItem operation: Cannot do "
                    "operations on a non-existent table")


@patch("src.services.s3_service.retrieve_file_url")
def test_retrieve_file_not_found(retrieveFileUrl_mock, test_client, audit_service_mock):
    file_key = 'test_file_key'
    expected_error_message = ('The file test_file_key could not be found')
    retrieveFileUrl_mock.side_effect = FileNotFoundException(f'The file {file_key} could not be found', file_key)

    response = test_client.get(f'/retrieve_file?file_key={file_key}')

    assert response.status_code == 404
    assert response.json()['detail'] == expected_error_message
    audit_service_mock.assert_called()


@patch("src.services.s3_service.retrieve_file_url")
def test_retrieve_unknown_exception(retrieveFileUrl_mock, test_client, audit_service_mock):
    file_key = 'test-file-key'
    retrieveFileUrl_mock.side_effect = Exception('unknown exception')

    response = test_client.get(f'/retrieve_file?file_key={file_key}')
    assert response.json()['detail'] == 'An error occurred while retrieving the file'
    assert response.status_code == 500
