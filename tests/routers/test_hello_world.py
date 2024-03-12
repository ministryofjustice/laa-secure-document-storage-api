from fastapi.testclient import TestClient
from src.main import app

test_client = TestClient(app)

def test_hello_world():
    response = test_client.get("/helloworld")

    assert response.status_code == 200

    assert response.json() == {"Hello": "World"}
