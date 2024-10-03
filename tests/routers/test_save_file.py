from io import BytesIO
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware import Middleware

from src.main import app

test_client = TestClient(app)


@patch("src.routers.save_file.saveToS3", return_value=True)
def test_save_file_with_valid_data(save_mock):
    remove_middleware(app, )

    data = {
        "body": '{"bucketName": "test_bucket"}'
    }

    files = {
        'file': ('test_file.txt', BytesIO(b'Test data'), 'text/plain')
    }

    response = test_client.post('/save_file', data=data, files=files)

    assert response.status_code == 200
    assert response.json()['success'] == 'Files Saved successfully in test_bucket with key test_file.txt '
    save_mock.assert_called_once()


def test_save_file_with_no_file():
    remove_middleware(app, )
    data = {
        "body": '{"bucketName": "test_bucket"}'
    }

    files = {"file": ("", BytesIO(), "text/plain")}
    response = test_client.post("/save_file", data=data, files=files)

    assert response.status_code == 400
    assert response.json() == {'detail': 'File is required'}


def test_save_file_with_invalid_data():
    remove_middleware(app, )
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


def test_save_file_with_missing_bucket_name():
    remove_middleware(app, )
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
