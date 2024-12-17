from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from starlette.middleware import Middleware

from src.main import app
from src.models.execeptions.file_not_found import FileNotFoundException
from tests.auth.authn import test_user_credentials
from tests.auth.authn import rebuild_middleware_with_acl

test_client = TestClient(app)


@patch("src.middleware.auth.BearerTokenAuthBackend.authenticate", return_value=test_user_credentials)
def test_retrieve_file_missing_key(mock_auth):
    # Act
    rebuild_middleware_with_acl(app,)

    response = test_client.get('/retrieve_file/')

    # Assert
    assert response.status_code == 400
    assert 'detail' in response.json()
    assert response.json()['detail'] == 'File key is missing'
    mock_auth.assert_called()


def remove_middleware(app: FastAPI) -> FastAPI:
    new_middlewares: list[Middleware] = []
    app.user_middleware = new_middlewares
    app.middleware_stack = app.build_middleware_stack()
    return app


def mock_get_item(service_id, file_key):
    raise Exception("An error occurred (ResourceNotFoundException) when calling the GetItem operation: Cannot do "
                    "operations on a non-existent table")


@patch("src.routers.retrieve_file.audit_service.put_item", return_value=True)
@patch("src.middleware.auth.BearerTokenAuthBackend.authenticate", return_value=test_user_credentials)
@patch("src.services.s3_service.retrieve_file_url")
def test_retrieve_file_not_found(retrieveFileUrl_mock, auth_mock, audit_mock):
    # Arrange
    rebuild_middleware_with_acl(app, )

    file_key = 'test_file_key'
    expected_error_message = ('The file test_file_key could not be found')
    retrieveFileUrl_mock.side_effect = FileNotFoundException(f'The file {file_key} could not be found', file_key)

    response = test_client.get(f'/retrieve_file?file_key={file_key}')

    assert response.status_code == 404
    assert response.json()['detail'] == expected_error_message
    audit_mock.assert_called()
    auth_mock.assert_called()


@patch("src.routers.retrieve_file.audit_service.put_item", return_value=True)
@patch("src.middleware.auth.BearerTokenAuthBackend.authenticate", return_value=test_user_credentials)
@patch("src.services.s3_service.retrieve_file_url")
def test_retrieve_unknown_exception(retrieveFileUrl_mock, auth_mock, audit_mock):
    file_key = 'test-file-key'
    retrieveFileUrl_mock.side_effect = Exception('unknown exception')

    response = test_client.get(f'/retrieve_file?file_key={file_key}')
    assert response.json()['detail'] == 'An error occurred while retrieving the file'
    assert response.status_code == 500
