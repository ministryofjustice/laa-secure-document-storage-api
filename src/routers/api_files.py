from fastapi import APIRouter

router = APIRouter()

@router.post("/files",status_code=201)
async def save_file():
    return {"message": "Hello World"}