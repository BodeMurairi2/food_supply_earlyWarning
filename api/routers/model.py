from fastapi import APIRouter, Depends, Query

from api import config
from api.controllers import model as controller
from api.dependencies import AppContext, get_context

router = APIRouter(prefix="/model")


@router.get("/performance")
def performance(ctx: AppContext = Depends(get_context)):
    return controller.performance(ctx)


@router.get("/feature-importance")
def feature_importance(model: str = Query("final", pattern="^(final|evaluation)$"), ctx: AppContext = Depends(get_context)):
    return controller.feature_importance(ctx, model)


@router.get("/explain")
def explain(district: str, year: int = Query(..., ge=config.TEST_YEARS[0], le=config.FORECAST_YEARS[1]),
            ctx: AppContext = Depends(get_context)):
    return controller.explain(ctx, district, year)
