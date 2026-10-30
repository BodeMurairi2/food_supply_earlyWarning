from fastapi import APIRouter, Depends, Query

from api.controllers import predictions as controller
from api.dependencies import AppContext, get_context
from api.routers.params import YEAR_RANGE
from api.schemas import PredictRequest, PredictResponse

router = APIRouter(prefix="/predict")


@router.get("/defaults")
def predict_defaults(district: str, year: int = Query(..., **YEAR_RANGE), ctx: AppContext = Depends(get_context)):
    return controller.defaults(ctx, district, year)


@router.post("", response_model=PredictResponse)
def predict(req: PredictRequest, ctx: AppContext = Depends(get_context)):
    return controller.predict(ctx, req)
