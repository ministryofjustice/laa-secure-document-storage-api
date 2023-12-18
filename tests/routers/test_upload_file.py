from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch

testClient = TestClient(app)

@patch("routers.upload_file.saveToS3")
def test_with_s3_save_success_responds_with_success(s3SaveMock, get_upload_file_request):
    #assign
    s3SaveMock.return_value = True
    #action
    response = testClient.post('/uploadFile', files = get_upload_file_request)
    #assert
    assert response.status_code == 200
    assert response.json() == {"success": True}

@patch("routers.upload_file.saveToS3")
def test_with_save_failure_throws_exception(s3SaveMock, get_upload_file_request):
    #assign
    s3SaveMock.return_value = False
    #action
    response = testClient.post('/uploadFile', files = get_upload_file_request)
    #assert
    assert response.status_code == 400
    assert response.json()['detail'] == "Something went wrong"