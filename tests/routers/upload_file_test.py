import httpx
from json.decoder import JSONDecodeError
import pytest
from unittest.mock import patch, call
from app import app
from models.validation_response import ValidationResponse
from fastapi.testclient import TestClient
from fastapi.encoders import jsonable_encoder

client = TestClient(app)


@pytest.mark.asyncio
@patch("app.upload_file.validate_request", return_value=ValidationResponse(status_code=200))
async def test_file_upload_success_expected_response(validate_file_mock, get_http_request_file):
    response = client.post("/uploadfile/", files=await get_http_request_file)
    assert response.status_code == 201 and response.json() == jsonable_encoder(good_upload_result())


@pytest.mark.asyncio
@patch("app.upload_file.validate_request", return_value=ValidationResponse(status_code=200))
async def test_file_upload_success_expected_log( validate_file_mock, get_http_request_file):
    _ = client.post("/uploadfile/", files=await get_http_request_file)
    assert mock_calls == [call.info("start_post_upload_file: filename='example.xlsx'"),
                                       call.info("upload_file_validation_success"),
                                       call.info("finish_post_upload_file: filename='example.xlsx'")]

@pytest.mark.asyncio
@pytest.mark.parametrize("status_code,message", [(411, ["content-length header not found"]),
                                                 (400, ["Content length does not exceed file size"]),
                                                 (413, ["File size suspiciously large (over 2000000 bytes)"])
                                                 ])
async def test_file_upload_fail_validation_response(status_code, message, get_http_request_file):
    with patch("app.upload_file.validate_request", return_value=ValidationResponse(status_code=status_code,
                                                                                   message=message)):
        response = client.post("/uploadfile/", files=await get_http_request_file)
    validation_response = ensure_validation_response_type(response)
    assert validation_response.status_code == status_code and validation_response.message == message


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code,message", [(411, ["content-length header not found"]),
                                                 (400, ["Content length does not exceed file size"]),
                                                 (413, ["File size suspiciously large (over 2000000 bytes)"])
                                                 ])


def ensure_validation_response_type(response: ValidationResponse | httpx.Response) -> ValidationResponse:
    if isinstance(response, ValidationResponse):
        validation_response = response
    elif isinstance(response, httpx.Response):
        message = []
        try:
            response_json = response.json()
        except JSONDecodeError:
            pass
        else:
            if isinstance(response_json, dict):
                message = response_json.get("detail", [])
        validation_response = ValidationResponse(status_code=response.status_code, message=message)
    return validation_response