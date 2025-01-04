from io import BytesIO
from unittest.mock import patch

from src.models.validation_response import ValidationResponse


@patch("src.routers.save_file.s3_service.save", return_value=True)
@patch("src.routers.save_file.validate_request")
def test_save_file_with_valid_data(validator_mock, save_mock, config_service_mock, audit_service_mock, test_client):
    validator_mock.return_value = ValidationResponse(status_code=200, message="")

    data = {
        "body": '{"bucketName": "test_bucket"}'
    }

    files = {
        'file': ('test_file.txt', BytesIO(b'Test data'), 'text/plain')
    }

    response = test_client.post('/save_file', data=data, files=files)

    assert response.status_code == 200
    assert response.json()['success'] == 'Files Saved successfully in test_bucket with key test_file.txt '

    validator_mock.assert_called()
    config_service_mock.assert_called()
    save_mock.assert_called_once()
    audit_service_mock.assert_called()


def test_save_file_with_no_file(test_client):
    data = {
        "body": '{"bucketName": "test_bucket"}'
    }

    files = {"file": ("", BytesIO(), "text/plain")}
    response = test_client.post("/save_file", data=data, files=files)

    assert response.status_code == 400
    assert response.json() == {'detail': ['File is required']}


def test_save_file_with_invalid_data(test_client):
    data = {
        "body": 'bad body'
    }

    files = {
        'file': ('test_file.txt', BytesIO(b'Test data'), 'text/plain')
    }

    response = test_client.post("/save_file", data=data, files=files)

    assert response.status_code == 400
    content = response.content
    print(content)


def test_save_file_with_missing_bucket_name(test_client):
    data = {
        "body": '{}'
    }

    files = {
        'file': ('test_file.txt', BytesIO(b'Test data'), 'text/plain')
    }

    response = test_client.post('/save_file', data=data, files=files)

    assert response.status_code == 400
    assert response.content == b'{"detail":{"bucketName":"Field required"}}'
