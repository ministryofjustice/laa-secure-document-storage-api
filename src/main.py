# main.py
from fastapi import FastAPI
from src.routers import hello_world


app = FastAPI()

app.include_router(hello_world.router)
