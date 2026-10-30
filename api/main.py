"""HarvestWatch API.

Run from the repository root:
    uvicorn api.main:app --reload --port 8000
"""

import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import config
from api.dependencies import build_context
from api.routers import api_router
from api.routers.frontend import router as frontend_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.context = build_context()
    yield


app = FastAPI(title="HarvestWatch API", version="0.1.0",
              description="District food insecurity forecasts for Rwanda (random forest, NISR CFSVA target).",
              lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["GET", "POST"], allow_headers=["*"])
app.include_router(api_router)
app.include_router(frontend_router)  # last, because it catches every other path

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        port=8000,
        reload=True
    )
