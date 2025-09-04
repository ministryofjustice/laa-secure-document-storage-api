import asyncio
import time
import structlog
from fastapi import APIRouter

router = APIRouter()
logger = structlog.get_logger()


@router.get("/ping")
async def health(sleep: float = 2.0):
    """
    Reachability test, always return 200 OK with JSON {'ping': 'pong'}
    """
    start_time = time.time()
    asyncio.sleep(sleep)
    duration = time.time() - start_time
    logger.info(f"ping sleep {sleep:10.4f}s took {duration:10.4f}s")

    return {"ping": "pong"}
