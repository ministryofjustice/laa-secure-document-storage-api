import os

import pytest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi_authz import CasbinMiddleware
from starlette.authentication import AuthCredentials, SimpleUser
from starlette.middleware.authentication import AuthenticationMiddleware

from src.middleware.auth import BearerTokenAuthBackend
from src.models.client_config import ClientConfig
from src.services.authz_service import AuthzService
from src.services import client_config_service


@pytest.fixture
def test_user_credentials() -> tuple[AuthCredentials, SimpleUser]:
    return AuthCredentials(scopes=[]), SimpleUser('test_user')


@pytest.fixture
def test_user_client_config(test_user_credentials):
    return ClientConfig(
        azure_client_id=test_user_credentials[1].username, bucket_name='test_bucket', azure_display_name='test'
    )


class TestAuthBackend(BearerTokenAuthBackend):
    def __init__(self, user_credentials: tuple[AuthCredentials, SimpleUser]):
        self.user_credentials = user_credentials

    async def authenticate(self, request):
        return self.user_credentials


@pytest.fixture(autouse=True)
def app_with_test_auth(test_user_credentials) -> FastAPI:
    from src.main import app
    test_files_model: str = 'casbin_model_acl.conf'
    test_files_policy: str = 'casbin_policy_allow_test_user.csv'
    os.environ['CASBIN_MODEL'] = os.path.join('tests', 'fixtures', test_files_model)
    os.environ['CASBIN_POLICY'] = os.path.join('tests', 'fixtures', test_files_policy)
    AuthzService._instance = None
    if app.middleware_stack is not None:
        app.middleware_stack = None
    if len(app.user_middleware) > 0:
        app.user_middleware.clear()
    app.add_middleware(CasbinMiddleware, enforcer=AuthzService().enforcer)
    app.add_middleware(AuthenticationMiddleware, backend=TestAuthBackend(test_user_credentials))
    app.middleware_stack = app.build_middleware_stack()
    return app


@pytest.fixture(autouse=True)
def test_client_unmodified() -> TestClient:
    from src.main import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def test_client(test_client_unmodified: TestClient, app_with_test_auth: FastAPI) -> TestClient:
    """
    TestClient using app_with_test_auth fixture, hence works with authentication and authorisation intact for the
    test_user_credentials fixture.

    :param test_client_unmodified:
    :param app_with_test_auth:
    :return:
    """
    return TestClient(app_with_test_auth)


@pytest.fixture
def auth_service_mock(test_user_credentials):
    """
    Occasional helper where the normal test_client is too broad,
    mock the authenticate method of the BearerTokenAuthBackend class to return the test_user_credentials fixture.
    """
    with patch.object(
            BearerTokenAuthBackend, "authenticate",
            return_value=(test_user_credentials[0], test_user_credentials[1])
    ) as mock_auth_backend:
        yield mock_auth_backend


@pytest.fixture
def config_service_mock(test_user_client_config):
    with patch.object(
            client_config_service, "get_config_for_client",
            return_value=test_user_client_config
    ) as mock:
        yield mock
