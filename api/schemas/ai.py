"""Models for the AI Analyst."""

from typing import Optional

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    district: str = Field(..., max_length=40)
    year: int = Field(..., ge=2021, le=2026, description="2021-2024: test years; 2025-2026: forecasts")
    question: Optional[str] = Field(None, max_length=300, description="Optional research question")


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=300)
    max_results: int = Field(5, ge=1, le=10)
