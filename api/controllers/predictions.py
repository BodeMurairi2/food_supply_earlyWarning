"""Prediction Lab."""

from api.controllers.errors import guarded
from api.services import predictions as predictions_service


def defaults(ctx, district, year):
    return guarded(predictions_service.inputs_for, ctx, district, year)


def predict(ctx, req):
    return guarded(predictions_service.predict, ctx, req.district, req.year, req.inputs)
