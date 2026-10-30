"""AI Analyst: an ADK agent (LLM through LiteLLM/OpenRouter) that researches a model result with Tavily.

The numbers (prediction, risk, SHAP drivers, history) come from the saved model and the dataset and are
passed to the agent as fixed context. The agent can only cite web results it actually received: every
search result gets an id (S1, S2, ...) and the response keeps only citations to ids that exist.
"""

import asyncio
from datetime import datetime, timezone

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.genai import types

from api import config
from api.agents.errors import AIUnavailable, AIUpstreamError
from api.agents.instruction.analyst import INSTRUCTION
from api.agents.instruction.assistant import ASSISTANT_INSTRUCTION
from api.agents.memory.session import APP_NAME, USER_ID, new_session
from api.agents.parsing import clean_analysis, clean_briefing, parse_json
from api.agents.prompt.analyst import build_message
from api.agents.prompt.assistant import build_message as build_assistant_message
from api.agents.tool.search import make_search_tool


def _require_keys():
    status = config.ai_status()
    if not status["llm"]:
        raise AIUnavailable("The AI model is not configured: set OPENROUTER_API_KEY in .env")
    if not status["search"]:
        raise AIUnavailable("Web search is not configured: set TAVILY_API_KEY in .env")


async def _run_agent(instruction, message, generate_config=None):
    """Run the agent once; return its final text, the sources it retrieved and its searches."""
    sources, searches = [], []
    agent = LlmAgent(name="harvestwatch_analyst", model=LiteLlm(model=config.LLM_MODEL), instruction=instruction,
                     tools=[make_search_tool(sources, searches)], generate_content_config=generate_config)
    sessions, session = await new_session()
    runner = Runner(app_name=APP_NAME, agent=agent, session_service=sessions)

    async def collect():
        final = ""
        async for event in runner.run_async(user_id=USER_ID, session_id=session.id, new_message=message):
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
    return text, sources, searches


def _generated_at():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


async def run_analysis(context, question=None):
    _require_keys()
    text, sources, searches = await _run_agent(INSTRUCTION, build_message(context, question))
    analysis, dropped = clean_analysis(parse_json(text), {s["id"] for s in sources})
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


async def run_assistant(kind, context):
    """The longer explanation on the Prediction Lab, Forecasts and Visualizations pages."""
    _require_keys()
    generate_config = types.GenerateContentConfig(max_output_tokens=config.AI_ASSISTANT_MAX_TOKENS)
    text, sources, searches = await _run_agent(ASSISTANT_INSTRUCTION, build_assistant_message(kind, context), generate_config)
    raw = parse_json(text)
    briefing, _ = clean_briefing(raw, {s["id"] for s in sources})

    # Keep at most 6 sources, cited ones first, and only citations to sources the reader can open.
    cited = {i for sec in ("evidence", "actions") for x in briefing[sec] for i in x["sources"]}
    ordered = sorted(sources, key=lambda s: s["id"] not in cited)[:config.AI_ASSISTANT_MAX_SOURCES]
    briefing, dropped = clean_briefing(raw, {s["id"] for s in ordered})
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
