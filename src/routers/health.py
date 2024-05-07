import structlog
from fastapi import APIRouter

router = APIRouter()
logger = structlog.get_logger()


@router.get("/")
@router.get("/health")
async def health():
    return {"Health": "OK"}
