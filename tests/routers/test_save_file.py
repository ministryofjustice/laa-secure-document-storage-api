from io import BytesIO
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware import Middleware

from src.models.validation_response import ValidationResponse
from src.main import app

from tests.auth.authn import rebuild_middleware_with_acl, test_user_credentials
from tests.auth.authz import test_user_client_config

test_client = TestClient(app)


@patch("src.dependencies.get_config_for_client", return_value=test_user_client_config)
@patch("src.middleware.auth.BearerTokenAuthBackend.authenticate", return_value=test_user_credentials)
@patch("src.routers.save_file.save_to_s3", return_value=True)
@patch("src.routers.save_file.validate_request")
def test_save_file_with_valid_data(validator_mock, save_mock, mock_auth, mock_config):
    rebuild_middleware_with_acl(app, )
    validator_mock.return_value = ValidationResponse(status_code=200, message="")

    data = {
        "body": '{"bucketName": "test_bucket"}'
    }

    files = {
        'file': ('test_file.txt', BytesIO(b'Test data'), 'text/plain')
    }

    response = test_client.post('/save_file', data=data, files=files)
    mock_config.assert_called()
    assert response.status_code == 200
    assert response.json()['success'] == 'Files Saved successfully in test_bucket with key test_file.txt '
    save_mock.assert_called_once()
    mock_auth.assert_called()
    mock_config.assert_called()


@patch("src.middleware.auth.BearerTokenAuthBackend.authenticate", return_value=test_user_credentials)
def test_save_file_with_no_file(mock_auth):
    rebuild_middleware_with_acl(app, )
    data = {
        "body": '{"bucketName": "test_bucket"}'
    }

    files = {"file": ("", BytesIO(), "text/plain")}
    response = test_client.post("/save_file", data=data, files=files)

    assert response.status_code == 400
    assert response.json() == {'detail': ['File is required']}


@patch("src.middleware.auth.BearerTokenAuthBackend.authenticate", return_value=test_user_credentials)
def test_save_file_with_invalid_data(mock_auth):
    rebuild_middleware_with_acl(app, )
    data = {
        "body": 'bad body'
    }

    files = {
        'file': ('test_file.txt', BytesIO(b'Test data'), 'text/plain')
    }

    response = test_client.post("/save_file", data=data, files=files)

    assert response.status_code == 400
    content = response.content
    print(content)


@patch("src.middleware.auth.BearerTokenAuthBackend.authenticate", return_value=test_user_credentials)
def test_save_file_with_missing_bucket_name(mock_auth):
    rebuild_middleware_with_acl(app, )
    data = {
        "body": '{}'
    }

    files = {
        'file': ('test_file.txt', BytesIO(b'Test data'), 'text/plain')
    }

    response = test_client.post('/save_file', data=data, files=files)

    assert response.status_code == 400
    assert response.content == b'{"detail":{"bucketName":"Field required"}}'


def remove_middleware(app: FastAPI) -> FastAPI:
    new_middlewares: list[Middleware] = []
    app.user_middleware = new_middlewares
    app.middleware_stack = app.build_middleware_stack()
    return app
