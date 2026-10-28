"""Request and response models for the HarvestWatch API."""

from typing import Optional

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    district: str = Field(..., description="District name, e.g. 'Nyamasheke'")
    year: int = Field(..., ge=2006, le=2026, description="Target year (survey year t)")
    inputs: dict[str, Optional[float]] = Field(
        default_factory=dict,
        description="Feature values to use instead of the dataset row. null = leave empty (imputed by the model).",
    )


class Contribution(BaseModel):
    feature: str
    label: str
    group: str
    unit: str
    value: Optional[float | str | int] = None
    contribution: float


class HistoryPoint(BaseModel):
    year: int
    observed: Optional[float]
    observation_type: Optional[str]


class PredictResponse(BaseModel):
    district: str
    province: str
    year: int
    prediction: float = Field(..., description="Predicted % of households food insecure (0-100)")
    risk: Optional[str]
    base_value: float
    contributions: list[Contribution]
    missing_inputs_imputed: list[str]
    history: list[HistoryPoint]
    dataset_value_this_year: Optional[float]
    model: str
    note: str


class HealthResponse(BaseModel):
    status: str
    dataset_rows: int
    models_loaded: list[str]


class AnalyzeRequest(BaseModel):
    district: str = Field(..., max_length=40)
    year: int = Field(..., ge=2021, le=2026, description="2021-2024: test years; 2025-2026: forecasts")
    question: Optional[str] = Field(None, max_length=300, description="Optional research question")


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=300)
    max_results: int = Field(5, ge=1, le=10)
