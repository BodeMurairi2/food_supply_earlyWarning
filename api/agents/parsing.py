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
