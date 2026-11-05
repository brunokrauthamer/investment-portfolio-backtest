"""ASGI application entry point."""

from fastapi import FastAPI

from backend.src.api.controller.health import router as health_router
from backend.src.api.controller.portfolio import router as portfolio_router

app = FastAPI()
app.include_router(health_router)
app.include_router(portfolio_router)
