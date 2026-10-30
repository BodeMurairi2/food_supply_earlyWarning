from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.controllers import overview as controller
from api.dependencies import AppContext, get_context
from api.routers.params import YEAR_RANGE

router = APIRouter()


@router.get("/overview")
def overview(province: Optional[str] = None, district: Optional[str] = None,
             year: int = Query(2025, **YEAR_RANGE), ctx: AppContext = Depends(get_context)):
    return controller.overview(ctx, province, district, year)
