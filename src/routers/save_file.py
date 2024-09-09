import structlog
from fastapi import APIRouter, HTTPException

router = APIRouter()
logger = structlog.get_logger()


@router.post('/save_file')
async def save_file():
    raise HTTPException(
        status_code=501,
        detail="Not implemented yet."
    )
