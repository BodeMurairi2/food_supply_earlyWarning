"""The structure the AI must answer in. The agent receives these as its output schema, and every answer is validated against them."""

from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field


def _as_list(value):
    return [value] if isinstance(value, str) else value


Paragraphs = Annotated[list[str], BeforeValidator(_as_list)]
Scope = Literal["district", "province", "national", "regional"]
Credibility = Literal["high", "medium", "low"]
SOURCE_IDS = "Ids of the search results that support this, e.g. S1. Only ids returned by search_web."


class Evidence(BaseModel):
    finding: str = Field(description="Fact stated by the source")
    sources: list[str] = Field(description=SOURCE_IDS)
    scope: Scope = Field(description="The area the finding is really about")
    credibility: Credibility
    relevance: str = Field(description="Why it matters for this area")


# ---------- AI Analyst ----------
class AnalystDriver(BaseModel):
    feature: str = Field(description="Label from the context")
    direction: Literal["raises", "lowers"]
    points: float = Field(description="The contribution from the context, rounded to 1 decimal")
    explanation: str = Field(description="What this input is and why it may matter; association, not proof")


class AnalystScenario(BaseModel):
    scenario: str = Field(description="If ... then ...")
    uncertainty: str = Field(description="What could change it")


class AnalystRecommendation(BaseModel):
    action: str = Field(description="Practical measure")
    rationale: str = Field(description="Why, tied to drivers or evidence")
    sources: list[str] = Field(default_factory=list, description=SOURCE_IDS)


class AnalystOutput(BaseModel):
    interpretation: str = Field(description="2-4 sentences: what the predicted percentage means, with the risk class and how it compares with the district's surveys")
    drivers: list[AnalystDriver] = Field(description="The 3-6 largest contributions from the context")
    external_evidence: list[Evidence]
    implications_2027: list[AnalystScenario]
    recommendations: list[AnalystRecommendation]
    limitations: Paragraphs = Field(description="Data gaps, model error (about 5-6 points on real surveys), evidence gaps")


# ---------- AI assistant ----------
class Driver(BaseModel):
    factor: str = Field(description="Name from the context")
    direction: Literal["raises", "lowers", "neutral"]
    explanation: str = Field(description="2-3 sentences on what it is and why it may matter; association, not proof")


class Scenario(BaseModel):
    scenario: str = Field(description="If ... then ...")
    implication: str = Field(description="What it would mean for households and planners")


class Outlook(BaseModel):
    assessment: Paragraphs = Field(description="2-3 full paragraphs of reasoned, conditional judgement")
    watch_for: Paragraphs = Field(description="Specific signs to monitor")
    scenarios: list[Scenario]


class Action(BaseModel):
    action: str = Field(description="Practical measure")
    who: str = Field(description="Who should act")
    when: str = Field(description="When")
    rationale: str = Field(description="Why, tied to the result or the evidence")
    sources: list[str] = Field(default_factory=list, description=SOURCE_IDS)


class AssistantOutput(BaseModel):
    headline: str = Field(description="One sentence with the main message")
    what_it_means: Paragraphs = Field(description="3-5 full paragraphs: what the result means in everyday terms, how it compares with the area's history and with the rest of Rwanda, and how confident to be")
    drivers: list[Driver]
    evidence: list[Evidence]
    outlook_3_6_months: Outlook = Field(description="What this implies for the next 3 to 6 months, tied to the agricultural calendar")
    outlook_1_year: Outlook = Field(description="What this implies over the next year")
    actions: list[Action]
    limitations: Paragraphs = Field(description="Data gaps, model error (about 5-6 points on real surveys), evidence gaps")
