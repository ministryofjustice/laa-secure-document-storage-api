import logging.config
import structlog
from fastapi import FastAPI
from structlog.stdlib import LoggerFactory
from asgi_correlation_id.context import correlation_id
from src.config import logging_config
from src.routers import health
from typing import Any


def add_correlation(
        logger: logging.Logger, method_name: str, event_dict: dict[str, Any]) \
        -> dict[str, Any]:
    # Add request id to log message.
    if request_id := correlation_id.get():
        event_dict["request_id"] = request_id
    return event_dict


app = FastAPI()

app.include_router(health.router)

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
                    wrapper_class=None,  # Set wrapper_class to None
                    cache_logger_on_first_use=True
                    )
logging.config.dictConfig(logging_config.config)
