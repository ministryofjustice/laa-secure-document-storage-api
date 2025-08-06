import structlog
from fastapi import APIRouter

from src.services import status_service

router = APIRouter()
logger = structlog.get_logger()


@router.get("/status")
async def status():
    """
    Gathers all supported status checks and returns the results as a JSON object.

    Always returns 200 OK with JSON status report

    See also /health which returns 503 SERVICE UNAVAILABLE if any check fails.
    """
    return await status_service.get_status()
