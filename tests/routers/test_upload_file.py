from fastapi.testclient import TestClient

import validation.validator
from main import app
from unittest.mock import patch
import pytest
from unittest.mock import patch
from models.validation_response import ValidationResponse

testClient = TestClient(app)


@patch("routers.upload_file.saveToS3")
@patch("routers.upload_file.validate_request")
def test_with_s3_save_and_validation_success_responds_with_success(validator_mock, s3_save_mock, get_upload_file_request):
    # assign
    s3_save_mock.return_value = True
    validator_mock.return_value = ValidationResponse(status_code=200, message="")
    # action
    response = testClient.post('/uploadFile', files =get_upload_file_request)
    # assert
    assert response.status_code == 200
    assert response.json() == {"success": True}


@patch("routers.upload_file.saveToS3")
@patch("routers.upload_file.validate_request")
def test_with_save_failure_throws_exception(validator_mock, s3_save_mock, get_upload_file_request):
    # assign
    s3_save_mock.return_value = False
    validator_mock.return_value = ValidationResponse(status_code=200, message="")
    # action
    response = testClient.post('/uploadFile', files=get_upload_file_request)
    # assert
    assert response.status_code == 400
    assert response.json()['detail'] == "Something went wrong"


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code,message", [(411, ["content-length header not found"]),
                                                 (400, ["Content length does not exceed file size"]),
                                                 (413, ["File size suspiciously large (over 2000000 bytes)"]),
                                                 (415, ["File is of wrong content type"]),
                                                 (400, ["Virus Found"])
                                                 ])
@patch("routers.upload_file.validate_request")
async def test_file_upload_with_fail_validation_response(validator_mock, status_code, message, get_upload_file_request):
    validator_mock.return_value = ValidationResponse(status_code=status_code, message=message)
    response = testClient.post("/uploadFile/", files=get_upload_file_request)
    response_json = response.json()
    assert response.status_code == status_code and response_json['detail'] == message
