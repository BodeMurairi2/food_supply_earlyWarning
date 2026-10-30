"""Errors raised by the AI Analyst."""


class AIUnavailable(Exception):
    """A required key is missing (-> HTTP 503)."""


class AIUpstreamError(Exception):
    """The LLM or search provider failed (-> HTTP 502)."""
