from typing import Optional

from fastapi import APIRouter, Depends, Query

from api import config
from api.controllers import historical as controller
from api.dependencies import AppContext, get_context

router = APIRouter()


@router.get("/historical")
def historical(province: Optional[str] = None, district: Optional[str] = None,
               year: Optional[int] = Query(None, ge=config.TEST_YEARS[0], le=config.TEST_YEARS[1]),
               ctx: AppContext = Depends(get_context)):
    return controller.historical(ctx, province, district, year)
