from fastapi.testclient import TestClient
from src.main import app

client=TestClient(app)

def test_upload_file():
    response = client.post("/files", files={"file": ("testfile.txt", b"dummy content", "text/plain")},
        data={"name": "dummy_file_1", "reference": "12345"})
    assert response.status_code == 201
    assert response.json()["file_name"] == "dummy_file_1"

def test_upload_file_without_name():
    response = client.post("/files", files={"file": ("testfile.txt", b"dummy content", "text/plain")},
        data={"reference": "12345"})
    assert response.status_code == 422
    error_detail = response.json()['detail'][0]
    assert error_detail['loc'][-1] == 'name'
    assert error_detail['msg'] == 'Field required'

def test_upload_file_without_file_and_name():
    response = client.post("/files", data={"reference": "12345"})
    assert response.status_code == 422
    assert response.status_code == 422
    error_detail = response.json()['detail'][0]
    assert error_detail['loc'][-1] == 'file'
    assert error_detail['msg'] == 'Field required'
    error_detail = response.json()['detail'][1]
    assert error_detail['loc'][-1] == 'name'
    assert error_detail['msg'] == 'Field required'

def test_upload_file_without_reference():
    response = client.post("/files", files={"file": ("testfile.txt", b"dummy content", "text/plain")},
        data={"name": "dummy_file_1"})
    assert response.status_code == 201
    assert response.json()["file_name"] == "dummy_file_1"