from fastapi.testclient import TestClient
from src.main import app

test_client = TestClient(app)


def test_hello_world():
    response = test_client.get("/helloworld")

    assert response.status_code == 200

    assert response.json() == {"Hello": "World"}
    assert response.json() == {"Hello": "Trying to break flake8 max line-length by making a line over 119 characters in length."}
