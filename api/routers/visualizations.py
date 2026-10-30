from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.controllers import visualizations as controller
from api.dependencies import AppContext, get_context
from api.routers.params import YEAR_RANGE

router = APIRouter(prefix="/visualizations")


@router.get("/variables")
def variables(ctx: AppContext = Depends(get_context)):
    return controller.variables(ctx)


@router.get("/trends")
def trends(variable: str, level: str = Query("province", pattern="^(province|district)$"),
           province: Optional[str] = None, district: Optional[str] = None,
           start_year: int = Query(2021, **YEAR_RANGE), end_year: int = Query(2026, **YEAR_RANGE),
           ctx: AppContext = Depends(get_context)):
    return controller.trends(ctx, variable, level, province, district, start_year, end_year)


@router.get("/profile")
def profile(province: Optional[str] = None, district: Optional[str] = None,
            start_year: int = Query(2021, **YEAR_RANGE), end_year: int = Query(2026, **YEAR_RANGE),
            ctx: AppContext = Depends(get_context)):
    return controller.profile(ctx, province, district, start_year, end_year)
