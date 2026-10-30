from typing import Optional

from fastapi import APIRouter, Depends

from api.controllers import forecasts as controller
from api.dependencies import AppContext, get_context

router = APIRouter()


@router.get("/forecasts")
def forecasts(province: Optional[str] = None, district: Optional[str] = None, ctx: AppContext = Depends(get_context)):
    return controller.forecasts(ctx, province, district)


@router.get("/district-series")
def district_series(district: str, ctx: AppContext = Depends(get_context)):
    return controller.district_series(ctx, district)
