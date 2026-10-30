"""Model performance, feature importance and explanations."""

from api.controllers.errors import guarded
from api.services import model_insights


def performance(ctx):
    return model_insights.performance(ctx)


def feature_importance(ctx, model):
    return model_insights.feature_importance(ctx, "final" if model == "final" else "evaluation")


def explain(ctx, district, year):
    return guarded(model_insights.explain, ctx, district, year)
