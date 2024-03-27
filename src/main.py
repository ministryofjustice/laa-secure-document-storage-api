# main.py
from fastapi import FastAPI
from src.routers import health


app = FastAPI()

app.include_router(health.router)
