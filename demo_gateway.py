import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
import httpx

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "frontend" / "dist"
BACKEND_URL = "http://127.0.0.1:8000"

if not (DIST / "index.html").is_file():
    raise RuntimeError("Production frontend not found. Run npm run build first.")

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_api(path: str, request: Request):
    # Forward API requests to the existing backend without exposing its port directly.
    url = f"{BACKEND_URL}/api/{path}"
    headers = {
        key: value for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length", "connection"}
    }
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=False) as client:
        upstream = await client.request(
            request.method,
            url,
            params=request.query_params,
            content=await request.body(),
            headers=headers,
        )
    excluded = {"content-encoding", "content-length", "transfer-encoding", "connection"}
    response_headers = {
        key: value for key, value in upstream.headers.items()
        if key.lower() not in excluded
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
    )

@app.get("/{path:path}")
async def frontend(path: str):
    candidate = (DIST / path).resolve()
    if candidate.is_relative_to(DIST.resolve()) and candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(
        DIST / "index.html",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )
