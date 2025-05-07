from io import BytesIO
from unittest.mock import patch, MagicMock
import pytest
from fastapi import HTTPException

from src.handlers.file_upload_handler import handle_file_upload_logic
from src.models.validation_response import ValidationResponse
from src.utils.request_types import RequestType


# =========================== SUCCESSS =========================== #


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "request_type, file_existed, expected_success_message",
    [
        (RequestType.PUT, False, "File saved successfully in test_bucket with key test_file.txt"),
        (RequestType.PUT, True, "File updated successfully in test_bucket with key test_file.txt"),
        (RequestType.POST, False, "File saved successfully in test_bucket with key test_file.txt"),
    ],
    # IDs make test output more readable for parametrized tests
    ids=[
        "PUT_new_file_success",
        "PUT_existing_file_success",
        "POST_new_file_success",
    ]
)
@patch("src.handlers.file_upload_handler.s3_service.save", return_value=True)
@patch("src.handlers.file_upload_handler.s3_service.file_exists")
@patch("src.handlers.file_upload_handler.audit_service.put_item")
@patch("src.handlers.file_upload_handler.clam_av_validator.scan_request",
       return_value=ValidationResponse(status_code=200, message=""))
@patch("src.handlers.file_upload_handler.client_configured_validator.validate_or_error")
async def test_handle_file_upload_success(
    validate_or_error_mock,
    scan_request_mock,
    audit_put_item_mock,
    file_exists_mock,
    save_mock,
    request_type,
    file_existed,
    expected_success_message,
):
    request = MagicMock(headers={})
    file = MagicMock()
    file.filename = "test_file.txt"
    file.file = BytesIO(b"Test content")
    body = MagicMock()
    body.model_dump.return_value = {"bucketName": "test_bucket"}
    client_config = MagicMock()
    client_config.bucket_name = "test_bucket"
    client_config.azure_display_name = "Test Client"

    file_exists_mock.return_value = file_existed

    response, file_existed_return = await handle_file_upload_logic(
        request=request,
        file=file,
        body=body,
        client_config=client_config,
        request_type=request_type,
        )

    assert response["success"] == expected_success_message
    assert file_existed_return == file_existed
    audit_put_item_mock.assert_called_once()
    save_mock.assert_called_once()
    scan_request_mock.assert_called_once()
    validate_or_error_mock.assert_called_once()
    file_exists_mock.assert_called_once()


# =========================== FAILURE =========================== #

@pytest.mark.asyncio
@patch("src.handlers.file_upload_handler.clam_av_validator.scan_request",
       return_value=ValidationResponse(status_code=200, message=""))
@patch("src.handlers.file_upload_handler.s3_service.file_exists", return_value=True)
@patch("src.handlers.file_upload_handler.client_configured_validator.validate_or_error")
async def test_handle_file_upload_POST_existing_file_failure(
    validate_or_error_mock,
    file_exists_mock,
    scan_request_mock
):
    request = MagicMock(headers={})
    file = MagicMock()
    file.filename = "preexisting_test_file.txt"
    file.file = BytesIO(b"Test content")
    body = MagicMock()
    body.model_dump.return_value = {"bucketName": "test_bucket"}
    client_config = MagicMock()
    client_config.bucket_name = "test_bucket"
    client_config.azure_display_name = "Test Client"

    with pytest.raises(HTTPException) as exc_info:
        await handle_file_upload_logic(
            request=request,
            file=file,
            body=body,
            client_config=client_config,
            request_type=RequestType.POST,
            )

    assert exc_info.value.status_code == 409
    assert f"File {file.filename} already exists and cannot be overwritten" in str(exc_info.value.detail)
    scan_request_mock.assert_called_once()
    validate_or_error_mock.assert_called_once()
    file_exists_mock.assert_called_once()


@pytest.mark.asyncio
@patch("src.handlers.file_upload_handler.clam_av_validator.scan_request")
async def test_handle_file_upload_antivirus_failure(scan_request_mock):

    scan_request_mock.return_value = ValidationResponse(status_code=400, message="Virus detected")

    request = MagicMock(headers={})
    file = MagicMock()
    file.filename = "infected_file.txt"
    file.file = BytesIO(b"Bad content")

    body = MagicMock()
    body.model_dump.return_value = {"bucketName": "test_bucket"}

    client_config = MagicMock()
    client_config.bucket_name = "test_bucket"
    client_config.azure_display_name = "Test Client"

    with pytest.raises(HTTPException) as exc_info:
        await handle_file_upload_logic(
            request=request,
            file=file,
            body=body,
            client_config=client_config,
            request_type=RequestType.POST
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Virus detected"

    scan_request_mock.assert_called_once()


@pytest.mark.asyncio
@patch("src.handlers.file_upload_handler.s3_service.save", return_value=False)
@patch("src.handlers.file_upload_handler.s3_service.file_exists", return_value=False)
@patch("src.handlers.file_upload_handler.audit_service.put_item")
@patch("src.handlers.file_upload_handler.clam_av_validator.scan_request")
@patch("src.handlers.file_upload_handler.client_configured_validator.validate_or_error")
async def test_handle_file_upload_save_failure(
    validate_or_error_mock,
    scan_request_mock,
    audit_put_item_mock,
    file_exists_mock,
    save_mock,
):
    scan_request_mock.return_value = ValidationResponse(status_code=200, message="")

    request = MagicMock(headers={})
    file = MagicMock()
    file.filename = "test_file.txt"
    file.file = BytesIO(b"Test content")

    body = MagicMock()
    body.model_dump.return_value = {"bucketName": "test_bucket"}

    client_config = MagicMock()
    client_config.bucket_name = "test_bucket"
    client_config.azure_display_name = "Test Client"

    with pytest.raises(HTTPException) as exc_info:
        await handle_file_upload_logic(
            request=request,
            file=file,
            body=body,
            client_config=client_config,
            request_type=RequestType.POST
        )

    assert exc_info.value.status_code == 500
    assert "failed to save" in str(exc_info.value.detail)

    scan_request_mock.assert_called_once()
    validate_or_error_mock.assert_called_once()
    audit_put_item_mock.assert_called_once()
    save_mock.assert_called_once()
    file_exists_mock.assert_called_once()
