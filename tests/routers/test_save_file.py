from unittest.mock import patch
from fastapi import HTTPException
from io import BytesIO


# =========================== SUCCESS =========================== #


@patch("src.routers.save_file.handle_file_upload_logic")
def test_save_file_new_file(handler_mock, test_client):
    handler_mock.return_value = (
        {"success": "File saved successfully in test_bucket with key test_file.txt"},
        False
    )

    data = {
        "body": '{"bucketName": "test_bucket"}'
    }
    files = {
        "file": ("test_file.txt", BytesIO(b"Test content"), "text/plain")
    }

    response = test_client.put("/save_file", data=data, files=files)

    assert response.status_code == 201
    assert response.json() == {"success": "File saved successfully in test_bucket with key test_file.txt"}

    handler_mock.assert_called_once()


@patch("src.routers.save_file.handle_file_upload_logic")
def test_save_file_update_existing_file(handler_mock, test_client):
    handler_mock.return_value = (
        {"success": "File saved successfully in test_bucket with key test_file.txt"},
        True
    )

    data = {
        "body": '{"bucketName": "test_bucket"}'
    }
    files = {
        "file": ("test_file.txt", BytesIO(b"Test content"), "text/plain")
    }

    response = test_client.put("/save_file", data=data, files=files)

    assert response.status_code == 200
    assert response.json() == {"success": "File saved successfully in test_bucket with key test_file.txt"}

    handler_mock.assert_called_once()


# =========================== FAILURE =========================== #


@patch("src.routers.save_file.handle_file_upload_logic")
def test_save_file_with_virus(handler_mock, test_client):
    handler_mock.side_effect = HTTPException(status_code=400, detail="Virus detected")

    data = {
        "body": '{"bucketName": "test_bucket"}'
    }
    files = {
        "file": ("infected_file.txt", BytesIO(b"malicious content"), "text/plain")
    }

    response = test_client.put("/save_file", data=data, files=files)

    assert response.status_code == 400
    assert response.json() == {"detail": "Virus detected"}

    handler_mock.assert_called_once()


def test_save_file_with_no_file(test_client):
    data = {
        "body": '{"bucketName": "test_bucket"}'
    }

    files = {"file": ("", BytesIO(), "text/plain")}
    response = test_client.put("/save_file", data=data, files=files)

    assert response.status_code == 400
    assert response.json() == {'detail': ['File is required']}


def test_save_file_with_invalid_data(test_client):
    data = {
        "body": 'bad body'
    }

    files = {
        'file': ('test_file.txt', BytesIO(b'Test data'), 'text/plain')
    }

    response = test_client.put("/save_file", data=data, files=files)

    assert response.status_code == 400
    content = response.content
    print(content)


def test_save_file_with_missing_bucket_name(test_client):
    data = {
        "body": '{}'  # Missing required field 'bucketName'
    }

    files = {
        'file': ('test_file.txt', BytesIO(b'Test data'), 'text/plain')
    }

    response = test_client.put('/save_file', data=data, files=files)

    assert response.status_code == 400
    assert response.json() == {"detail": {"bucketName": "Field required"}}
