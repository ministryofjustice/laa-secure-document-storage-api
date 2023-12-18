from fastapi import FastAPI

from routers import hello_world as hello_world_router
from routers import upload_file as upload_file_router

app = FastAPI()

app.include_router(hello_world_router.router)
app.include_router(upload_file_router.router)