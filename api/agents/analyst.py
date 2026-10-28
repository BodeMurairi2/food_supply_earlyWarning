"""AI Analyst: an ADK agent (LLM through LiteLLM/OpenRouter) that researches a model result with Tavily.

The numbers (prediction, risk, SHAP drivers, history) come from the saved model and the dataset and are
passed to the agent as fixed context. The agent can only cite web results it actually received: every
search result gets an id (S1, S2, ...) and the response keeps only citations to ids that exist.
"""

import asyncio
import json
import os
import re
import uuid
from datetime import datetime, timezone

import httpx
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from api import config


class AIUnavailable(Exception):
    """A required key is missing (-> HTTP 503)."""


class AIUpstreamError(Exception):
    """The LLM or search provider failed (-> HTTP 502)."""


async def tavily_search(query, max_results=config.AI_RESULTS_PER_SEARCH):
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        raise AIUnavailable("Web search is not configured: set TAVILY_API_KEY in .env")
    body = {"query": query, "max_results": max_results, "search_depth": config.SEARCH_DEPTH, "include_answer": False}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(config.TAVILY_URL, json=body, headers={"Authorization": f"Bearer {key}"})
    except httpx.HTTPError as e:
        raise AIUpstreamError(f"Tavily request failed: {type(e).__name__}") from e
    if r.status_code != 200:
        raise AIUpstreamError(f"Tavily returned HTTP {r.status_code}")
    return [{"title": x.get("title") or x.get("url"), "url": x.get("url"),
             "snippet": (x.get("content") or "")[:700], "published_date": x.get("published_date"),
             "score": x.get("score")} for x in r.json().get("results", []) if x.get("url")]


INSTRUCTION = """You are HarvestWatch's food security analyst for Rwanda. You explain one district's model result
for decision makers (NISR, MINAGRI, district agriculture officers, WFP).

You receive MODEL CONTEXT as JSON: the district, the year, the model's predicted share of households food insecure
(CARI, moderately + severely), its risk class, SHAP feature contributions (percentage points added to or removed from
the model's average), the district's survey history and recent climate/harvest/price inputs.

Workflow:
1. Read the model context. Its numbers are final: never change, recompute or invent model outputs or contributions.
2. Call `search_web` 2 to 4 times with focused queries, e.g. rainfall or climate outlook for Rwanda/East Africa,
   crop production or harvest for the district or province, food or staple prices in Rwanda, floods/landslides/drought.
   Include the district or province name and recent years in queries. Add the user's question if one is given.
3. Judge each result for credibility (official/UN/research > news > blogs), recency, geography and relevance.
   Ignore weak or off-topic results.
4. Answer with ONE JSON object and nothing else (no markdown fences), using exactly this shape:
{
  "interpretation": "2-4 sentences: what the predicted percentage means, with the risk class and how it compares with the district's surveys.",
  "drivers": [{"feature": "label from the context", "direction": "raises" | "lowers", "points": number, "explanation": "what this input is and why it may matter; association, not proof"}],
  "external_evidence": [{"finding": "fact stated by the source", "sources": ["S1"], "scope": "district" | "province" | "national" | "regional", "credibility": "high" | "medium" | "low", "relevance": "why it matters for this district"}],
  "implications_2027": [{"scenario": "if ... then ...", "uncertainty": "what could change it"}],
  "recommendations": [{"action": "practical measure", "rationale": "why, tied to drivers or evidence", "sources": ["S2"]}],
  "limitations": ["data gaps, model error (about 5-6 points on real surveys), evidence gaps"]
}

Rules:
- "drivers": the 3-6 largest contributions from the context, with the same points (rounded to 1 decimal).
- Cite only ids returned by search_web (S1, S2, ...). Never write URLs, titles, dates, quotes or statistics that are not
  in the search results or the model context. If no reliable evidence is found, return an empty external_evidence
  list and say so in limitations.
- National or regional findings are not confirmed district conditions: set "scope" honestly.
- 2027 is outside the model's range: give conditional scenarios only, never a predicted 2027 value.
- Associations in the model are not causes. Keep the language plain and short."""


def _parse_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise AIUpstreamError("The model did not return a structured answer")
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        raise AIUpstreamError("The model returned malformed JSON") from e


def _clean_analysis(raw, source_ids):
    """Keep the expected sections only, and drop citations to sources that were never retrieved."""
    def ids(item):
        return [s for s in item.get("sources", []) if s in source_ids] if isinstance(item, dict) else []

    def items(key):
        v = raw.get(key, [])
        return [x for x in v if isinstance(x, dict)] if isinstance(v, list) else []

    evidence = [dict(x, sources=ids(x)) for x in items("external_evidence")]
    dropped = sum(1 for x in evidence if not x["sources"])
    evidence = [x for x in evidence if x["sources"]]   # a web "fact" without a real source is not shown
    return {
        "interpretation": str(raw.get("interpretation", "")),
        "drivers": items("drivers"),
        "external_evidence": evidence,
        "implications_2027": items("implications_2027"),
        "recommendations": [dict(x, sources=ids(x)) for x in items("recommendations")],
        "limitations": [str(x) for x in raw.get("limitations", []) if x] if isinstance(raw.get("limitations"), list) else [],
    }, dropped


async def run_analysis(context, question=None):
    status = config.ai_status()
    if not status["llm"]:
        raise AIUnavailable("The AI model is not configured: set OPENROUTER_API_KEY in .env")
    if not status["search"]:
        raise AIUnavailable("Web search is not configured: set TAVILY_API_KEY in .env")

    sources, searches = [], []

    async def search_web(query: str) -> dict:
        """Search the web for recent evidence about Rwanda's climate, harvests, food prices or shocks.

        Args:
            query: A focused search query, e.g. "Rwanda Western Province rainfall forecast 2026".

        Returns:
            Results with an id (S1, S2, ...), title, url, snippet and publication date when known.
        """
        if len(searches) >= config.AI_MAX_SEARCHES:
            return {"error": f"Search limit reached ({config.AI_MAX_SEARCHES}). Write the answer now."}
        searches.append(query)
        results = await tavily_search(query)
        out = []
        for r in results:
            existing = next((s for s in sources if s["url"] == r["url"]), None)
            if existing is None:
                existing = dict(r, id=f"S{len(sources) + 1}", query=query)
                sources.append(existing)
            out.append({k: existing[k] for k in ("id", "title", "url", "snippet", "published_date")})
        return {"query": query, "results": out}

    agent = LlmAgent(name="harvestwatch_analyst", model=LiteLlm(model=config.LLM_MODEL),
                     instruction=INSTRUCTION, tools=[search_web])
    sessions = InMemorySessionService()
    runner = Runner(app_name="harvestwatch", agent=agent, session_service=sessions)
    session = await sessions.create_session(app_name="harvestwatch", user_id="analyst", session_id=uuid.uuid4().hex)

    prompt = "MODEL CONTEXT:\n" + json.dumps(context, ensure_ascii=False)
    if question:
        prompt += f"\n\nUSER QUESTION (research this too): {question}"
    message = types.Content(role="user", parts=[types.Part(text=prompt)])

    async def collect():
        final = ""
        async for event in runner.run_async(user_id="analyst", session_id=session.id, new_message=message):
            if event.error_message:
                raise AIUpstreamError(f"LLM error: {event.error_message}")
            if event.is_final_response() and event.content and event.content.parts:
                final = "".join(p.text or "" for p in event.content.parts)
        return final

    try:
        text = await asyncio.wait_for(collect(), timeout=config.AI_TIMEOUT_S)
    except asyncio.TimeoutError as e:
        raise AIUpstreamError(f"The analysis took longer than {config.AI_TIMEOUT_S} s and was stopped") from e
    except (AIUnavailable, AIUpstreamError):
        raise
    except Exception as e:  # LiteLLM raises provider-specific errors (bad key, unknown model, rate limit)
        raise AIUpstreamError(f"LLM request failed ({type(e).__name__}): {str(e)[:300]}") from e

    analysis, dropped = _clean_analysis(_parse_json(text), {s["id"] for s in sources})
    cited = {i for sec in ("external_evidence", "recommendations") for x in analysis[sec] for i in x["sources"]}
    warnings = []
    if dropped:
        warnings.append(f"{dropped} evidence item(s) without a valid source were removed.")
    if not sources:
        warnings.append("No web results were retrieved; the analysis relies on model output only.")
    return {
        "analysis": analysis,
        "sources": [dict(s, cited=s["id"] in cited) for s in sources],
        "searches": searches,
        "llm_model": config.LLM_MODEL,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "warnings": warnings,
    }
