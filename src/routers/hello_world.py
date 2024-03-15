from fastapi import APIRouter

router = APIRouter()


@router.get("/helloworld/")
async def hello_world():
    return {"Hello": "World"}


def indent_size_example():
        print("Hello, World!")
