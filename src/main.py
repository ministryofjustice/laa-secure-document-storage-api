from fastapi import FastAPI

from src.routers import hello_world as hello_world_router
from src.routers import api_files as api_files_router

app = FastAPI()

app.include_router(hello_world_router.router)
app.include_router(api_files_router.router)