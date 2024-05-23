import logging.config
from typing import Any

import structlog
from asgi_correlation_id.context import correlation_id
from fastapi import FastAPI
from structlog.stdlib import LoggerFactory

from src.config import logging_config
from src.routers import health as health_router
from src.routers import retrieve_file as retrieve_router


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
app.include_router(health_router.router)
app.include_router(retrieve_router.router)
