"""Translate service and AI errors into HTTP responses."""

from fastapi import HTTPException

from api.agents.errors import AIUnavailable, AIUpstreamError


def guarded(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e).strip("'\""))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


async def ai_guarded(coro):
    try:
        return await coro
    except AIUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except AIUpstreamError as e:
        raise HTTPException(status_code=502, detail=str(e))
