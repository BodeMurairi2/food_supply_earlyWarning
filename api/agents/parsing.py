"""Check the agent's answer against its output schema, and keep only citations to real sources."""

import re

from pydantic import ValidationError


class InvalidOutput(Exception):
    """The answer does not match the output schema."""


def parse_output(text, schema):
    """Validated model for the agent's final text. Tolerates code fences around the JSON."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip())
    try:
        return schema.model_validate_json(text)
    except ValidationError as e:
        raise InvalidOutput(str(e)[:500]) from e


def _keep_cited(items, source_ids):
    return [dict(x, sources=[s for s in x["sources"] if s in source_ids]) for x in items]


def _real_evidence(items, source_ids):
    """A web "fact" without a real source is not shown. Returns the items kept and the number dropped."""
    kept = [x for x in _keep_cited(items, source_ids) if x["sources"]]
    return kept, len(items) - len(kept)


def clean_briefing(output, source_ids):
    data = output.model_dump()
    data["evidence"], dropped = _real_evidence(data["evidence"], source_ids)
    data["actions"] = _keep_cited(data["actions"], source_ids)
    return data, dropped
