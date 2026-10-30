"""Web search for the AI Analyst (Tavily REST API).

Every result gets an id (S1, S2, ...), so the analysis can only cite sources that were actually retrieved.
"""

import os

import httpx

from api import config
from api.agents.errors import AIUnavailable, AIUpstreamError


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


def make_search_tool(sources, searches):
    """Build the agent's search tool for one analysis; it records what it finds in the two lists."""

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

    return search_web
