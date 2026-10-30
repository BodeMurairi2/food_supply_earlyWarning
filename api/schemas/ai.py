"""Models for the AI Analyst."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=300)
    max_results: int = Field(5, ge=1, le=10)


class AssistantRequest(BaseModel):
    """What the user is looking at. The numbers are always recomputed on the server."""
    kind: Literal["prediction", "historical", "forecast", "visualization"]
    district: Optional[str] = Field(None, max_length=40)
    province: Optional[str] = Field(None, max_length=40)
    year: Optional[int] = Field(None, ge=2006, le=2026)
    inputs: dict[str, Optional[float]] = Field(default_factory=dict, description="Prediction Lab inputs")
    variable: Optional[str] = Field(None, max_length=60)
    level: Literal["province", "district"] = "province"
    start_year: int = Field(2021, ge=2006, le=2026)
    end_year: int = Field(2026, ge=2006, le=2026)
    question: Optional[str] = Field(None, max_length=300, description="Optional research question")
