"""Forecasts and district histories."""

from api.controllers.errors import guarded
from api.services import forecasts as forecasts_service


def forecasts(ctx, province, district):
    return guarded(forecasts_service.forecast_table, ctx, province, district)


def district_series(ctx, district):
    return guarded(forecasts_service.district_series, ctx, district)
