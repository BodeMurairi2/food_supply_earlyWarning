"""Models for the system endpoints."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    dataset_rows: int
    models_loaded: list[str]
