import logging.config
import os
from typing import Any

import sentry_sdk
import structlog
from asgi_correlation_id.context import correlation_id
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from structlog.stdlib import LoggerFactory
from fastapi_authz import CasbinMiddleware

from src.config import logging_config
from src.middleware.auth import BearerTokenAuthBackend, BearerTokenMiddleware
from src.services.authz_service import AuthzService

from src.routers import retrieve_file
from src.routers import save_or_update_file
from src.routers import save_file
from src.routers import bulk_upload
from src.routers import delete_files
from src.routers import virus_check_file
from src.routers import scan_for_suspicious_content
from src.routers import status
from src.routers import ping
from src.routers import health
from src.routers import root
from src.routers import available_validators
from src.routers import file_details


def add_correlation(
        logger: logging.Logger, method_name: str, event_dict: dict[str, Any]) \
        -> dict[str, Any]:
    """processor function for structlog that adds correlation ID to log messages """
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

app = FastAPI(
    title='LAA Secure Document Storage API',
    version='0.8.0'
)

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
app.add_middleware(CasbinMiddleware, enforcer=AuthzService().enforcer)
app.add_middleware(BearerTokenMiddleware, backend=BearerTokenAuthBackend())
app.add_middleware(CorrelationIdMiddleware)


app.include_router(retrieve_file.router)
app.include_router(retrieve_file.router, prefix="/api/v1")

app.include_router(save_or_update_file.router)
app.include_router(save_or_update_file.router, prefix="/api/v1")

app.include_router(save_file.router)
app.include_router(save_file.router, prefix="/api/v1")

app.include_router(bulk_upload.router)
app.include_router(bulk_upload.router, prefix="/api/v1")

app.include_router(delete_files.router)
app.include_router(delete_files.router, prefix="/api/v1")

app.include_router(virus_check_file.router)
app.include_router(virus_check_file.router, prefix="/api/v1")

app.include_router(scan_for_suspicious_content.router)
app.include_router(scan_for_suspicious_content.router, prefix="/api/v1")

app.include_router(status.router)
app.include_router(status.router, prefix="/api/v1")

app.include_router(ping.router)
app.include_router(ping.router, prefix="/api/v1")

app.include_router(health.router)
app.include_router(health.router, prefix="/api/v1")

app.include_router(root.router)
app.include_router(root.router, prefix="/api/v1")

app.include_router(available_validators.router)
app.include_router(available_validators.router, prefix="/api/v1")

app.include_router(file_details.router)
app.include_router(file_details.router, prefix="/api/v1")
