from fastapi.testclient import TestClient
from src.main import app

client=TestClient(app)

def test_upload_file():
    response = client.post("/files", files={"file": ("testfile.txt", b"dummy content", "text/plain")},
        data={"name": "dummy_file_1", "reference": "12345"})
    assert response.status_code == 201
    assert response.json()["file_name"] == "dummy_file_1"