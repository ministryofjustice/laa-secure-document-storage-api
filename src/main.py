from fastapi import FastAPI, HTTPException
import sentry_sdk
import logging.config
from typing import Any
import structlog
from asgi_correlation_id.context import correlation_id
from httpx import Request
from structlog.stdlib import LoggerFactory

from src.config import logging_config
from src.routers import health as health_router
from src.routers import retrieve_file as retrieve_router
from src.middleware.auth import bearer_token_middleware

# Initialize Sentry
sentry_sdk.init(
    dsn="https://02c5e4a686e2a1f58c3329be0bd51138@o345774.ingest.us.sentry.io/4507815741030400",
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)


def add_correlation(
        logger: logging.Logger, method_name: str, event_dict: dict[str, Any]) \
        -> dict[str, Any]:
    if request_id := correlation_id.get():
        event_dict["request_id"] = request_id
    return event_dict


app = FastAPI()

structlog.configure(logger_factory=LoggerFactory(), processors=[
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


# Apply middleware to all routes except /test-error
@app.middleware("http")
async def custom_middleware(request: Request, call_next):
    if request.url.path == "/test-error":
        response = await call_next(request)
        return response
    return await bearer_token_middleware(request, call_next)


app.include_router(health_router.router)
app.include_router(retrieve_router.router)
