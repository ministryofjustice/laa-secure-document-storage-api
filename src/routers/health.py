import structlog
from fastapi import APIRouter

router = APIRouter()
logger = structlog.get_logger()


@router.get("/health")
async def health():
    logger.info("health_check_request_received")
    return {"Health": "OK"}
