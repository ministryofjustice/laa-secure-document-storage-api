from fastapi.testclient import TestClient
from src.main import app

test_client = TestClient(app)


def test_health():
    response = test_client.get("/health")

    assert response.status_code == 200

    assert response.json() == {"Hello": "World"}
