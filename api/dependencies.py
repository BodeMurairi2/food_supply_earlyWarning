"""What every request needs: the dataset and the models, created once at startup."""

from dataclasses import dataclass

from fastapi import Request

from api.data.dataset import Dataset
from api.model.registry import ModelRegistry


@dataclass
class AppContext:
    dataset: Dataset
    models: ModelRegistry


def build_context() -> AppContext:
    dataset = Dataset()
    models = ModelRegistry(dataset)
    # Precompute predictions and SHAP values once, so requests stay fast.
    _ = models.historical, models.forecasts, models.historical_class_probabilities
    return AppContext(dataset, models)


def get_context(request: Request) -> AppContext:
    return request.app.state.context
