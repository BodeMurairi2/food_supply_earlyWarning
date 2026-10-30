"""Historical analysis."""

from api.controllers.errors import guarded
from api.services import historical as historical_service


def historical(ctx, province, district, year):
    return guarded(historical_service.historical_table, ctx, province, district, year)
