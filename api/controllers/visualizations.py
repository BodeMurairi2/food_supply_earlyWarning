"""Visualizations."""

from api.controllers.errors import guarded
from api.services import visualizations as viz_service


def variables(ctx):
    return viz_service.viz_variables(ctx)


def trends(ctx, variable, level, province, district, start_year, end_year):
    return guarded(viz_service.viz_trends, ctx, variable, level, province, district, start_year, end_year)


def profile(ctx, province, district, start_year, end_year):
    return guarded(viz_service.viz_profile, ctx, province, district, start_year, end_year)
