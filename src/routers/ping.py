from fastapi import APIRouter

router = APIRouter()


@router.get("/ping")
async def health():
    """
    Reachability test, always return 200 OK with JSON {'ping': 'pong'}
    """
    return {"ping": "pong"}
