"""AI Analyst and AI assistant: rate limits, the analysis cache and running the agent."""

from fastapi import HTTPException, Request

from api import config
from api.agents.analyst import run_analysis, run_assistant
from api.agents.memory.cache import analysis_cache
from api.agents.tool.search import tavily_search
from api.controllers.errors import ai_guarded, guarded
from api.services.ai_context import ai_context, assistant_context
from api.services.ratelimit import RateLimiter

_limiter = RateLimiter(config.AI_LIMIT_PER_CLIENT_HOUR, config.AI_LIMIT_PER_DAY)


def _rate_limit(request: Request):
    message = _limiter.check(request.client.host if request.client else "unknown")
    if message:
        raise HTTPException(status_code=429, detail=message)


def status():
    return config.ai_status()


def context(ctx, district, year):
    return guarded(ai_context, ctx, district, year)


async def search(req, request):
    _rate_limit(request)
    results = await ai_guarded(tavily_search(req.query, req.max_results))
    return {"query": req.query, "results": results}


async def analyze(ctx, req, request):
    question = (req.question or "").strip() or None
    key = (req.district, req.year, question)
    if key in analysis_cache:
        return {**analysis_cache[key], "cached": True}
    model_context = guarded(ai_context, ctx, req.district, req.year)
    _rate_limit(request)
    result = await ai_guarded(run_analysis(model_context, question))
    out = {"district": req.district, "year": req.year, "question": question, "context": model_context, **result}
    analysis_cache[key] = out
    return {**out, "cached": False}


async def assistant(ctx, req, request):
    key = ("assistant", req.model_dump_json())
    if key in analysis_cache:
        return {**analysis_cache[key], "cached": True}
    model_context = guarded(assistant_context, ctx, req)
    _rate_limit(request)
    result = await ai_guarded(run_assistant(req.kind, model_context))
    out = {"kind": req.kind, **result}
    analysis_cache[key] = out
    return {**out, "cached": False}
