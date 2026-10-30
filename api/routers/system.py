from fastapi import APIRouter, Depends

from api.controllers import system as controller
from api.dependencies import AppContext, get_context
from api.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(ctx: AppContext = Depends(get_context)):
    return controller.health(ctx)


@router.get("/metadata")
def metadata(ctx: AppContext = Depends(get_context)):
    return controller.metadata(ctx)


@router.get("/locations")
def locations(ctx: AppContext = Depends(get_context)):
    return controller.locations(ctx)


@router.get("/boundaries")
def boundaries(ctx: AppContext = Depends(get_context)):
    return controller.boundaries(ctx)
