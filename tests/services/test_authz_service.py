from unittest.mock import patch
import os
import uuid

import pytest
import structlog
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi_authz import CasbinMiddleware
from starlette.authentication import AuthCredentials, SimpleUser, UnauthenticatedUser
from starlette.middleware.authentication import AuthenticationMiddleware

from src.main import app
from src.middleware.auth import BearerTokenAuthBackend
from src.services.authz_service import AuthzService

test_client = TestClient(app)
logger = structlog.get_logger()


def rebuild_middleware_with(app: FastAPI, model_file: str, policy_file: str) -> FastAPI:
    # Force authz service to create a new enforcer, picking up the specified model and policy files from env
    os.environ['CASBIN_MODEL'] = model_file
    os.environ['CASBIN_POLICY'] = policy_file
    AuthzService._instance = None
    if app.middleware_stack is not None:
        app.middleware_stack = None
    if len(app.user_middleware) > 0:
        app.user_middleware.clear()
    app.add_middleware(CasbinMiddleware, enforcer=AuthzService().enforcer)
    app.add_middleware(AuthenticationMiddleware, backend=BearerTokenAuthBackend())
    app.middleware_stack = app.build_middleware_stack()
    return app


@pytest.mark.parametrize("model_file,policy_file,username,expected_status,assert_msg", [
    (
        'casbin_model_acl.conf', 'casbin_policy_allow_test_user.csv', 'test_user', 200,
        'Specified user is allowed'
    ),
    (
        'casbin_model_acl.conf', 'casbin_policy_allow_test_user.csv', 'other_user', 403,
        'Different, but still authenticated, user is denied'
    ),
    (
        'casbin_model_acl.conf', 'casbin_policy_allow_test_user.csv', None, 403,
        'Unauthenticated user is denied'
    ),
    (
        'casbin_model_add_authenticated.conf', 'casbin_policy_allow_authenticated.csv', uuid.uuid4().hex, 200,
        'Model treats "authenticated" as special to allow an authenticated user'
    ),
    (
        'casbin_model_add_authenticated.conf', 'casbin_policy_allow_authenticated.csv', None, 403,
        'Model does not allow anonymous users to be matched against "authenticated"'
    ),
    (
        'casbin_model_add_authenticated.conf', 'casbin_policy_allow_any.csv', uuid.uuid4().hex, 200,
        'Model treats "*" as a wildcard, allowing any user'
    ),
    (
        'casbin_model_add_authenticated.conf', 'casbin_policy_allow_any.csv', None, 200,
        'Model treats "*" as a wildcard, allowing any user'
    )
])
def test_authz_service(model_file: str, policy_file: str, username: str | None, expected_status: int, assert_msg: str):
    rebuild_middleware_with(
        app,
        model_file=os.path.join('tests', 'testFiles', model_file),
        policy_file=os.path.join('tests', 'testFiles', policy_file)
    )
    request_user = SimpleUser(username) if username is not None else UnauthenticatedUser()
    with patch.object(
            BearerTokenAuthBackend, 'authenticate',
            return_value=(AuthCredentials(scopes=[]), request_user)
    ) as mock_auth_backend:
        response = test_client.get("/health")
        mock_auth_backend.assert_called()
        assert response.status_code == expected_status, assert_msg
