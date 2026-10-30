"""AI Analyst: an ADK agent (LLM through LiteLLM/OpenRouter) that researches a model result with Tavily.

The numbers (prediction, risk, SHAP drivers, history) come from the saved model and the dataset and are
passed to the agent as fixed context. The agent can only cite web results it actually received: every
search result gets an id (S1, S2, ...) and the response keeps only citations to ids that exist.
"""

import asyncio
import logging
from datetime import datetime, timezone

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.genai import types

from api import config
from api.agents.errors import AIUnavailable, AIUpstreamError
from api.agents.instruction.analyst import INSTRUCTION
from api.agents.instruction.assistant import ASSISTANT_INSTRUCTION
from api.agents.instruction.repair import REPAIR_INSTRUCTION
from api.agents.memory.session import APP_NAME, USER_ID, new_session
from api.agents.parsing import InvalidOutput, clean_analysis, clean_briefing, parse_output
from api.agents.prompt.analyst import build_message
from api.agents.prompt.assistant import build_message as build_assistant_message
from api.agents.tool.search import make_search_tool
from api.schemas import AnalystOutput, AssistantOutput

logger = logging.getLogger(__name__)


def _require_keys():
    status = config.ai_status()
    if not status["llm"]:
        raise AIUnavailable("The AI model is not configured: set OPENROUTER_API_KEY in .env")
    if not status["search"]:
        raise AIUnavailable("Web search is not configured: set TAVILY_API_KEY in .env")


async def _collect(runner, session_id, message):
    final = ""
    async for event in runner.run_async(user_id=USER_ID, session_id=session_id, new_message=message):
        if event.error_message:
            raise AIUpstreamError(f"LLM error: {event.error_message}")
        if event.is_final_response() and event.content and event.content.parts:
            final = "".join(p.text or "" for p in event.content.parts if not p.thought)
    return final


async def _call_agent(agent, message):
    """Run an agent to its final text, translating every failure into an AI error."""
    sessions, session = await new_session()
    runner = Runner(app_name=APP_NAME, agent=agent, session_service=sessions)
    try:
        return await asyncio.wait_for(_collect(runner, session.id, message), timeout=config.AI_TIMEOUT_S)
    except asyncio.TimeoutError as e:
        raise AIUpstreamError(f"The analysis took longer than {config.AI_TIMEOUT_S} s and was stopped") from e
    except (AIUnavailable, AIUpstreamError):
        raise
    except Exception as e:  # LiteLLM raises provider-specific errors (bad key, unknown model, rate limit)
        raise AIUpstreamError(f"LLM request failed ({type(e).__name__}): {str(e)[:300]}") from e


async def _run_agent(instruction, message, schema):
    """Research with the search tool and return an answer validated against `schema`, plus sources and searches."""
    sources, searches = [], []
    generate_config = types.GenerateContentConfig(max_output_tokens=config.AI_MAX_OUTPUT_TOKENS)
    agent = LlmAgent(name="harvestwatch_analyst", model=LiteLlm(model=config.LLM_MODEL), instruction=instruction,
                     tools=[make_search_tool(sources, searches)], output_schema=schema, generate_content_config=generate_config)
    text = await _call_agent(agent, message)
    try:
        return parse_output(text, schema), sources, searches
    except InvalidOutput as first:
        logger.warning("AI answer did not match %s: %s", schema.__name__, first)

    # One repair attempt: no tools and no new searches, so the sources found above stay the only ones.
    repair = LlmAgent(name="harvestwatch_formatter", model=LiteLlm(model=config.LLM_MODEL), instruction=REPAIR_INSTRUCTION,
                      output_schema=schema, generate_content_config=generate_config)
    prompt = "DRAFT:\n" + (text or "(empty)") + "\n\nORIGINAL REQUEST:\n" + "".join(p.text or "" for p in message.parts)
    fixed = await _call_agent(repair, types.Content(role="user", parts=[types.Part(text=prompt)]))
    try:
        return parse_output(fixed, schema), sources, searches
    except InvalidOutput as second:
        logger.warning("AI repair did not match %s: %s", schema.__name__, second)
        raise AIUpstreamError("The AI could not produce a complete answer this time. Please try again.") from second


def _generated_at():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


async def run_analysis(context, question=None):
    _require_keys()
    output, sources, searches = await _run_agent(INSTRUCTION, build_message(context, question), AnalystOutput)
    analysis, dropped = clean_analysis(output, {s["id"] for s in sources})
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
        "generated_at": _generated_at(),
        "warnings": warnings,
    }


def pick_sources(briefing, sources, limit):
    """Choose which sources to keep: one for each evidence item first, then other cited sources, then the rest."""
    wanted = []
    for item in briefing["evidence"]:
        if item["sources"] and not set(item["sources"]) & set(wanted):
            wanted.append(item["sources"][0])
    for item in briefing["evidence"] + briefing["actions"]:
        wanted += [i for i in item["sources"] if i not in wanted]
    rank = {source_id: position for position, source_id in enumerate(wanted)}
    return sorted(sources, key=lambda s: rank.get(s["id"], len(rank)))[:limit]


async def run_assistant(kind, context):
    """The longer explanation on the Prediction Lab, Forecasts and Visualizations pages."""
    _require_keys()
    output, sources, searches = await _run_agent(ASSISTANT_INSTRUCTION, build_assistant_message(kind, context), AssistantOutput)
    briefing, _ = clean_briefing(output, {s["id"] for s in sources})

    ordered = pick_sources(briefing, sources, config.AI_ASSISTANT_MAX_SOURCES)
    briefing, dropped = clean_briefing(output, {s["id"] for s in ordered})
    cited = {i for sec in ("evidence", "actions") for x in briefing[sec] for i in x["sources"]}

    warnings = []
    if dropped:
        warnings.append(f"{dropped} evidence item(s) without a valid source were removed.")
    if not ordered:
        warnings.append("No web results were retrieved; this explanation relies on the model and the dataset only.")
    return {
        "briefing": briefing,
        "sources": [dict(s, cited=s["id"] in cited) for s in ordered],
        "searches": searches,
        "llm_model": config.LLM_MODEL,
        "generated_at": _generated_at(),
        "warnings": warnings,
    }
