"""Overview dashboard."""

from api.controllers.errors import guarded
from api.services import overview as overview_service


def overview(ctx, province, district, year):
    return guarded(overview_service.overview, ctx, province, district, year)
