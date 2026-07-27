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
        error_report = status_report.get_failure_details()
        logger.error(f"Health check failure{error_report}")
        raise HTTPException(
            status_code=503,
            detail="Please try again later."
        )
    return {'Health': 'OK'}
