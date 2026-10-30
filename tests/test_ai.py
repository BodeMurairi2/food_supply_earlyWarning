"""AI Analyst tests with a scripted LLM and fake search results, so no keys or network are needed."""
import json

import pytest
from fastapi.testclient import TestClient
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from api.agents import analyst
from api.agents.memory.cache import analysis_cache
from api.agents.tool import search as search_tool
from api.main import app

FAKE_RESULTS = [
    {"title": "Rwanda seasonal rainfall outlook", "url": "https://example.org/outlook", "snippet": "Below-normal rain expected.",
     "published_date": "2026-02-01", "score": 0.9},
    {"title": "Western Province harvest report", "url": "https://example.org/harvest", "snippet": "Bean harvest fell.",
     "published_date": None, "score": 0.7},
]

ANSWER = {
    "interpretation": "About a third of households are expected to be food insecure.",
    "drivers": [{"feature": "Province", "direction": "raises", "points": 3.3, "explanation": "Location effect."}],
    "external_evidence": [
        {"finding": "Below-normal rain expected.", "sources": ["S1"], "scope": "national", "credibility": "high", "relevance": "Season A"},
        {"finding": "Invented claim.", "sources": ["S9"], "scope": "district", "credibility": "low", "relevance": "none"},
    ],
    "implications_2027": [{"scenario": "If rains fail, risk stays high.", "uncertainty": "Outlook skill is limited."}],
    "recommendations": [{"action": "Pre-position seed.", "rationale": "Rain outlook.", "sources": ["S1", "S7"]}],
    "limitations": ["Model error is about 5 points."],
}


class ScriptedLlm(BaseLlm):
    """First turn: call search_web. Second turn (after the tool result): return the JSON answer."""

    async def generate_content_async(self, llm_request, stream=False):
        answered = any(p.function_response for c in llm_request.contents for p in (c.parts or []))
        if not answered:
            part = types.Part(function_call=types.FunctionCall(name="search_web", args={"query": "Rwanda rainfall 2026"}))
        else:
            part = types.Part(text="```json\n" + json.dumps(ANSWER) + "\n```")
        yield LlmResponse(content=types.Content(role="model", parts=[part]))


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    monkeypatch.setenv("TAVILY_API_KEY", "test")
    monkeypatch.setattr(analyst, "LiteLlm", lambda model: ScriptedLlm(model="scripted"))

    async def fake_search(query, max_results=5):
        return FAKE_RESULTS

    monkeypatch.setattr(search_tool, "tavily_search", fake_search)
    analysis_cache.clear()
    with TestClient(app) as c:
        yield c


def test_analyze_runs_agent_and_keeps_only_real_citations(client):
    r = client.post("/api/ai/analyze", json={"district": "Rutsiro", "year": 2026})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["searches"] == ["Rwanda rainfall 2026"]
    assert [s["id"] for s in out["sources"]] == ["S1", "S2"]
    assert out["sources"][0]["cited"] and not out["sources"][1]["cited"]
    # The evidence item citing a non-existent S9 is removed; the fake S7 citation is stripped.
    assert len(out["analysis"]["external_evidence"]) == 1
    assert out["analysis"]["recommendations"][0]["sources"] == ["S1"]
    assert out["warnings"]
    # Model numbers come from the saved model, not from the LLM.
    assert out["context"]["model"]["prediction_pct"] == 32.7
    assert client.post("/api/ai/analyze", json={"district": "Rutsiro", "year": 2026}).json()["cached"]


def test_analyze_without_keys_is_503(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    analysis_cache.clear()
    with TestClient(app) as c:
        r = c.post("/api/ai/analyze", json={"district": "Huye", "year": 2025})
    assert r.status_code == 503
