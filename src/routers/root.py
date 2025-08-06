from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def root():
    """
    Simple landing page.
    """
    return {"detail": "Secure Document Storage API"}
