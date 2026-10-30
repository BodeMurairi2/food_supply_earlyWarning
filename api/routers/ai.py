from fastapi import APIRouter, Depends, Query, Request

from api import config
from api.controllers import ai as controller
from api.dependencies import AppContext, get_context
from api.schemas import AnalyzeRequest, AssistantRequest, SearchRequest

router = APIRouter(prefix="/ai")


@router.get("/status")
def status():
    return controller.status()


@router.get("/context")
def context(district: str, year: int = Query(..., ge=config.TEST_YEARS[0], le=config.FORECAST_YEARS[1]),
            ctx: AppContext = Depends(get_context)):
    return controller.context(ctx, district, year)


@router.post("/search")
async def search(req: SearchRequest, request: Request):
    return await controller.search(req, request)


@router.post("/analyze")
async def analyze(req: AnalyzeRequest, request: Request, ctx: AppContext = Depends(get_context)):
    return await controller.analyze(ctx, req, request)


@router.post("/assistant")
async def assistant(req: AssistantRequest, request: Request, ctx: AppContext = Depends(get_context)):
    return await controller.assistant(ctx, req, request)
