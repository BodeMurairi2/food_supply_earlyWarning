"""All API routes, under /api."""

from fastapi import APIRouter

from api.routers import ai, forecasts, historical, model, overview, predictions, system, visualizations

api_router = APIRouter(prefix="/api")
for module in (system, overview, historical, model, forecasts, predictions, visualizations, ai):
    api_router.include_router(module.router)
