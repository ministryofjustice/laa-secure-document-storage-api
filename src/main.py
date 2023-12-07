from fastapi import FastAPI

from routers import hello_world as hello_world_router

app = FastAPI()

app.include_router(hello_world_router.router)