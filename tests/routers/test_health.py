from fastapi.testclient import TestClient
from src.main import app

test_client = TestClient(app)
from tests.auth.authn import rebuild_middleware_with_acl


def test_health():
    rebuild_middleware_with_acl(app, )
    response = test_client.get("/health")

    assert response.status_code == 200

    assert response.json() == {"Health": "OK"}
