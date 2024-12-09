import logging.config
import os
from typing import Any

import sentry_sdk
import structlog
from asgi_correlation_id.context import correlation_id
from fastapi import FastAPI
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from starlette.middleware.authentication import AuthenticationMiddleware
from structlog.stdlib import LoggerFactory
from fastapi_authz import CasbinMiddleware

from src.config import logging_config
from src.middleware.auth import BearerTokenAuthBackend
from src.routers import health as health_router
from src.routers import retrieve_file as retrieve_router
from src.routers import save_file as save_router
from src.services.authz_service import AuthzServiceSingleton


def add_correlation(
        logger: logging.Logger, method_name: str, event_dict: dict[str, Any]) \
        -> dict[str, Any]:
    if request_id := correlation_id.get():
        event_dict["request_id"] = request_id
    return event_dict


sentry_dsn = os.environ.get('SENTRY_DSN')

if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,

        integrations=[
            StarletteIntegration(
                transaction_style="endpoint",
                failed_request_status_codes=[range(500, 599)],
            ),
            FastApiIntegration(
                transaction_style="endpoint",
                failed_request_status_codes=[range(500, 599)],
            ),
        ]
    )

app = FastAPI()

structlog.configure(
    logger_factory=LoggerFactory(), processors=[
        add_correlation,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M.%S"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=None,
    cache_logger_on_first_use=True
)

logging.config.dictConfig(logging_config.config)
# Order matters here: Casbin middleware first, then the auth backend
app.add_middleware(CasbinMiddleware, enforcer=AuthzServiceSingleton().enforcer)
app.add_middleware(AuthenticationMiddleware, backend=BearerTokenAuthBackend())
app.include_router(health_router.router)
app.include_router(retrieve_router.router)
app.include_router(save_router.router)
