from fastapi import APIRouter

router = APIRouter()


@router.get("/helloworld/")
async def hello_world():
    return {"Hello": "World"}

