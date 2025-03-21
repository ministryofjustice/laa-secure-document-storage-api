from fastapi import UploadFile, FastAPI
from io import BufferedReader
from unittest.mock import AsyncMock
import pytest
import os

from starlette.middleware import Middleware

pytest_plugins = [
    "tests.fixtures.auth",
    "tests.fixtures.audit",
]


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "normal_auth: mark test to run using normal auth middleware checks"
    )


@pytest.fixture()
def get_file() -> BufferedReader:
    test_file_path = os.path.join(
        os.getcwd(), "tests/testFiles/ss-poc-test.txt")
    file = open(test_file_path, "rb")
    return file


@pytest.fixture()
def get_upload_file_request(get_file) -> bytes:
    file = get_file
    return {"file": ("ss-poc-test.txt", file)}


@pytest.fixture()
def get_default_mock_file():
    test_file = AsyncMock(spec=UploadFile)
    test_file.read.return_value = b'test_file_content'
    test_file.size = 1234
    test_file.filename = 'test.txt'
    test_file.content_type = 'text/plain'
    return test_file


@pytest.fixture()
def app_without_middleware() -> FastAPI:
    from src.main import app
    new_middlewares: list[Middleware] = []
    app.user_middleware = new_middlewares
    app.middleware_stack = app.build_middleware_stack()
    return app
