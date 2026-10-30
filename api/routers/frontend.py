"""Serve the built frontend. Unknown paths return index.html so routes like /forecasts survive a page refresh."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from api import config

router = APIRouter()

if config.FRONTEND_DIST.is_dir():
    dist = config.FRONTEND_DIST.resolve()

    @router.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        file = (dist / path).resolve()
        if path and file.is_file() and file.is_relative_to(dist):
            return FileResponse(file)
        return FileResponse(dist / "index.html")
