"""Read the agent's JSON answer and keep only what can be trusted."""

import json
import re

from api.agents.errors import AIUpstreamError


def parse_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise AIUpstreamError("The model did not return a structured answer")
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        raise AIUpstreamError("The model returned malformed JSON") from e


def clean_analysis(raw, source_ids):
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


def clean_briefing(raw, source_ids):
    """The same checks for the AI assistant's longer answer."""
    def ids(item):
        return [s for s in item.get("sources", []) if s in source_ids]

    def items(source, key):
        v = source.get(key, [])
        return [x for x in v if isinstance(x, dict)] if isinstance(v, list) else []

    def texts(source, key):
        v = source.get(key, [])
        if isinstance(v, str):
            return [v]
        return [str(x) for x in v if x] if isinstance(v, list) else []

    def outlook(key):
        o = raw.get(key)
        o = o if isinstance(o, dict) else {}
        return {"assessment": texts(o, "assessment"), "watch_for": texts(o, "watch_for"), "scenarios": items(o, "scenarios")}

    evidence = [dict(x, sources=ids(x)) for x in items(raw, "evidence")]
    dropped = sum(1 for x in evidence if not x["sources"])
    return {
        "headline": str(raw.get("headline", "")),
        "what_it_means": texts(raw, "what_it_means"),
        "drivers": items(raw, "drivers"),
        "evidence": [x for x in evidence if x["sources"]],   # a web "fact" without a real source is not shown
        "outlook_3_6_months": outlook("outlook_3_6_months"),
        "outlook_1_year": outlook("outlook_1_year"),
        "actions": [dict(x, sources=ids(x)) for x in items(raw, "actions")],
        "limitations": texts(raw, "limitations"),
    }, dropped
