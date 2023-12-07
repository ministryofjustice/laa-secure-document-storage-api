from fastapi.testclient import TestClient
from src.main import app

client=TestClient(app)

def test_upload_file():
    response = client.post("/files")
    assert response.status_code == 201