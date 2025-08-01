import structlog
from fastapi import APIRouter, HTTPException

from src.services import status_service

router = APIRouter()
logger = structlog.get_logger()


@router.get("/health")
async def health():
    """
    * 200 OK with JSON {'Health': 'OK'} if all health checks pass
    * 503 SERVICE UNAVAILABLE with JSON {'detail': 'Please try again later'} if any checks fail
    """
    status_report = await status_service.get_status()
    if status_report.has_failures():
        raise HTTPException(
            status_code=503,
            detail="Please try again later."
        )
    return {'Health': 'OK'}
