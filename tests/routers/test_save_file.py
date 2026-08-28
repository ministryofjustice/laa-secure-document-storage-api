from unittest.mock import patch
from fastapi import HTTPException
from io import BytesIO
from src.models.file_upload import UploadFileResponse
# test_client fixture is defined in tests/fixtures/auth.py

# =========================== SUCCESS =========================== #


good_save_response = UploadFileResponse(success="File saved successfully in test_bucket with key test_file.txt",
                                        checksum="ABC123", version_id="1000000", file_already_existed=False)

good_update_response = UploadFileResponse(success="File updated successfully in test_bucket with key test_file.txt",
                                          checksum="DEF456", version_id="2000000", file_already_existed=True)

good_folder_save_response = UploadFileResponse(success="File saved successfully in test_bucket with key "
                                               "another_test_folder/test_file.txt",
                                               checksum="GHI789", version_id="3000000", file_already_existed=False)


@patch("src.routers.save_or_update_file.handle_file_upload_logic")
def test_save_or_update_file_new_file(handler_mock, test_client):
    handler_mock.return_value = good_save_response

    files = {
        "file": ("test_file.txt", BytesIO(b"Test content"), "text/plain")
    }

    response = test_client.put("/save_or_update_file", files=files)

    assert response.status_code == 201
    assert response.json() == {"success": "File saved successfully in test_bucket with key test_file.txt",
                               "checksum": "ABC123", "version_id": "1000000", "file_already_existed": False}

    handler_mock.assert_called_once()


@patch("src.routers.save_or_update_file.handle_file_upload_logic")
def test_save_or_update_file_update_existing(handler_mock, test_client):
    handler_mock.return_value = good_update_response

    files = {
        "file": ("test_file.txt", BytesIO(b"Updated test content"), "text/plain")
    }

    response = test_client.put("/save_or_update_file", files=files)

    assert response.status_code == 200
    assert response.json() == {"success": "File updated successfully in test_bucket with key test_file.txt",
                               "checksum": "DEF456", "version_id": "2000000", "file_already_existed": True}
    handler_mock.assert_called_once()


@patch("src.routers.save_or_update_file.handle_file_upload_logic")
def test_save_or_update_file_with_empty_body_processed_successfully(handler_mock, test_client):

    handler_mock.return_value = good_save_response

    data = {
        "body": '{}'
    }

    files = {
        'file': ('test_file.txt', BytesIO(b'Test data'), 'text/plain')
    }

    response = test_client.put('/save_or_update_file', data=data, files=files)

    assert response.status_code == 201
    assert response.json() == {"success": "File saved successfully in test_bucket with key test_file.txt",
                               "checksum": "ABC123", "version_id": "1000000", "file_already_existed": False}


# Body has syntactically correct json but data is irrelevant - success result
@patch("src.routers.save_or_update_file.handle_file_upload_logic")
def test_save_or_update_file_with_irrelevant_body_processed_successfully(handler_mock, test_client):

    handler_mock.return_value = good_save_response

    # Details below are not relevant as they do not correspond with FileUpload model
    data = {"body": '{"bucketName": "test_bucket", "speed": "extra slow"}'}

    files = {
        'file': ('test_file.txt', BytesIO(b'Test data'), 'text/plain')
    }

    response = test_client.put('/save_or_update_file', data=data, files=files)

    assert response.status_code == 201
    assert response.json() == {"success": "File saved successfully in test_bucket with key test_file.txt",
                               "checksum": "ABC123", "version_id": "1000000", "file_already_existed": False}


@patch("src.routers.save_or_update_file.handle_file_upload_logic")
def test_save_or_update_file_with_body_folder_value_processed_successfully(handler_mock, test_client):

    handler_mock.return_value = good_folder_save_response

    data = {"body": '{"folder": "another_test_folder"}'}

    files = {
        'file': ('test_file.txt', BytesIO(b'Test data'), 'text/plain')
    }

    response = test_client.put('/save_or_update_file', data=data, files=files)

    assert response.status_code == 201
    assert response.json() == {"success": "File saved successfully in test_bucket with key "
                               "another_test_folder/test_file.txt",
                               "checksum": "GHI789", "version_id": "3000000", "file_already_existed": False}
    # Check that the folder specified in request body has been forwarded to file handler in FileUpload object
    # Note will likley need updating if FileUpload model has new attributes
    assert "FileUpload(folder='another_test_folder')" in str(handler_mock.call_args)


# =========================== FAILURE =========================== #


@patch("src.routers.save_or_update_file.handle_file_upload_logic")
def test_save_or_update_file_with_virus(handler_mock, test_client):
    handler_mock.side_effect = HTTPException(status_code=400, detail="Virus detected")

    data = {
        "body": '{"bucketName": "test_bucket"}'
    }
    files = {
        "file": ("infected_file.txt", BytesIO(b"malicious content"), "text/plain")
    }

    response = test_client.put("/save_or_update_file", data=data, files=files)

    assert response.status_code == 400
    assert response.json() == {"detail": "Virus detected"}

    handler_mock.assert_called_once()


@patch("src.routers.save_or_update_file.handle_file_upload_logic")
def test_save_or_update_file_with_no_file(handler_mock, test_client):
    handler_mock.side_effect = HTTPException(status_code=400, detail=['File is required'])
    data = {
        "body": '{"bucketName": "test_bucket"}'
    }

    response = test_client.put("/save_or_update_file", data=data)

    assert response.status_code == 400
    assert response.json() == {'detail': ['File is required']}


# No patch because body validation takes place early in router before handler called
def test_save_or_update_file_with_invalid_data(test_client):
    data = {
        "body": 'bad body'
    }

    files = {
        'file': ('test_file.txt', BytesIO(b'Test data'), 'text/plain')
    }

    response = test_client.put("/save_or_update_file", data=data, files=files)

    assert response.status_code == 400
    assert "Invalid JSON" in response.text
