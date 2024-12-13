import os

from fastapi import FastAPI
from fastapi_authz import CasbinMiddleware
from starlette.authentication import AuthCredentials, SimpleUser
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware

from src.middleware.auth import BearerTokenAuthBackend
from src.services.authz_service import AuthzService

test_user_credentials = (AuthCredentials(scopes=[]), SimpleUser('test_user'))


def rebuild_middleware_with_acl(app: FastAPI, test_files_model: str = 'casbin_model_acl.conf', test_files_policy: str = 'casbin_policy_allow_test_user.csv') -> FastAPI:
    # Force authz service to create a new enforcer, picking up the specified model and policy files from env
    os.environ['CASBIN_MODEL'] = os.path.join('tests', 'auth', test_files_model)
    os.environ['CASBIN_POLICY'] = os.path.join('tests', 'auth', test_files_policy)
    AuthzService._instance = None
    if app.middleware_stack is not None:
        app.middleware_stack = None
    if len(app.user_middleware) > 0:
        app.user_middleware.clear()
    app.add_middleware(CasbinMiddleware, enforcer=AuthzService().enforcer)
    app.add_middleware(AuthenticationMiddleware, backend=BearerTokenAuthBackend())
    app.middleware_stack = app.build_middleware_stack()
    return app


def remove_middleware(app: FastAPI) -> FastAPI:
    new_middlewares: list[Middleware] = []
    app.user_middleware = new_middlewares
    app.middleware_stack = app.build_middleware_stack()
    return app
