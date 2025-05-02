from unittest.mock import patch
from io import BytesIO
from fastapi import HTTPException


# =========================== SUCCESS =========================== #


@patch("src.routers.upload_file.handle_file_upload_logic")
def test_upload_file_success(handler_mock, test_client):
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

    response = test_client.post("/upload_file", data=data, files=files)

    assert response.status_code == 201
    assert response.json() == {"success": "File saved successfully in test_bucket with key test_file.txt"}

    handler_mock.assert_called_once()


# =========================== FAILURE =========================== #


@patch("src.routers.upload_file.handle_file_upload_logic")
def test_upload_file_with_virus(handler_mock, test_client):
    handler_mock.side_effect = HTTPException(status_code=400, detail="Virus detected")

    data = {
        "body": '{"bucketName": "test_bucket"}'
    }
    files = {
        "file": ("infected_file.txt", BytesIO(b"malicious content"), "text/plain")
    }

    response = test_client.post("/upload_file", data=data, files=files)

    assert response.status_code == 400
    assert response.json() == {"detail": "Virus detected"}

    handler_mock.assert_called_once()


@patch("src.routers.upload_file.handle_file_upload_logic", return_value=({}, False))
def test_upload_file_no_file(handler_mock, test_client):

    handler_mock.side_effect = HTTPException(
        status_code=400,
        detail="File is required"
    )
    data = {
        "body": '{"bucketName": "test_bucket"}'
    }
    files = {
        "file": ("", BytesIO(), "text/plain")
    }

    response = test_client.post("/upload_file", data=data, files=files)

    assert response.status_code == 400
    assert response.json() == {'detail': 'File is required'}

    handler_mock.assert_called_once()


@patch("src.routers.upload_file.handle_file_upload_logic")
def test_upload_file_invalid_data(handler_mock, test_client):
    data = {
        "body": "bad body"
    }
    files = {
        "file": ("test_file.txt", BytesIO(b"Test content"), "text/plain")
    }

    response = test_client.post("/upload_file", data=data, files=files)

    assert response.status_code == 400

    handler_mock.assert_not_called()  # bad JSON fails before calling handler


@patch("src.routers.upload_file.handle_file_upload_logic")
def test_upload_file_missing_bucket_name(handler_mock, test_client):
    data = {
        "body": "{}"
    }
    files = {
        "file": ("test_file.txt", BytesIO(b"Test content"), "text/plain")
    }

    response = test_client.post("/upload_file", data=data, files=files)

    assert response.status_code == 400
    assert response.content == b'{"detail":{"bucketName":"Field required"}}'

    handler_mock.assert_not_called()  # validation error


@patch("src.routers.upload_file.handle_file_upload_logic")
def test_upload_file_existing_file(handler_mock, test_client):

    handler_mock.side_effect = HTTPException(
        status_code=409,
        detail="File already exists"
    )

    data = {
        "body": '{"bucketName": "test_bucket"}'
    }
    files = {
        "file": ("test_file.txt", BytesIO(b"Test content"), "text/plain")
    }

    response = test_client.post("/upload_file", data=data, files=files)

    assert response.status_code == 409
    assert response.json()["detail"] == "File already exists"

    handler_mock.assert_called_once()
