import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from utils.config import FAVICON_URL, LOGO_URL, MAX_RESULTS, PROJECT_ROOT, STREAM_INTERVAL_SECONDS
from utils.jalali import parse_jalali_datetime
from utils.logs import list_log_files, search_logs, serialize_entry, serialize_file
from utils.security import clear_session_cookie, create_session, require_user, set_session_cookie, validate_login


router = APIRouter()


class LoginPayload(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)
    totp: str = Field(min_length=6, max_length=12)


class SearchPayload(BaseModel):
    files: list[str] = Field(default_factory=list)
    query: str = Field(default="", max_length=500)
    levels: list[str] = Field(default_factory=list)
    start_jalali: str = Field(default="", max_length=32)
    end_jalali: str = Field(default="", max_length=32)
    start_gregorian: str = Field(default="", max_length=32)
    end_gregorian: str = Field(default="", max_length=32)
    recent_minutes: int | None = Field(default=None, ge=1, le=10080)
    limit: int = Field(default=200, ge=1, le=MAX_RESULTS)


def parse_gregorian_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.strip().replace("Z", ""))
    except ValueError:
        return None


# ---------- Page Routes ----------
@router.get("/")
async def index() -> FileResponse:
    return FileResponse(PROJECT_ROOT / "index.html")


@router.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@router.get("/api/config")
async def config() -> JSONResponse:
    return JSONResponse({"logo_url": LOGO_URL, "favicon_url": FAVICON_URL})


# ---------- Auth Routes ----------
@router.post("/api/login")
async def login(payload: LoginPayload) -> JSONResponse:
    if not validate_login(payload.username, payload.password, payload.totp):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    response = JSONResponse({"ok": True, "username": payload.username})
    set_session_cookie(response, create_session(payload.username))
    return response


@router.post("/api/logout")
async def logout() -> JSONResponse:
    response = JSONResponse({"ok": True})
    clear_session_cookie(response)
    return response


@router.get("/api/me")
async def me(username: str = Depends(require_user)) -> JSONResponse:
    return JSONResponse({"authenticated": True, "username": username})


# ---------- Log Routes ----------
@router.get("/api/files")
async def files(username: str = Depends(require_user)) -> JSONResponse:
    del username
    return JSONResponse({"files": [serialize_file(item) for item in list_log_files()]})


@router.post("/api/logs")
async def logs(payload: SearchPayload, username: str = Depends(require_user)) -> JSONResponse:
    del username
    start_at = parse_gregorian_datetime(payload.start_gregorian) or parse_jalali_datetime(payload.start_jalali)
    end_at = parse_gregorian_datetime(payload.end_gregorian) or parse_jalali_datetime(payload.end_jalali, end_of_day=True)
    entries, stats = search_logs(
        files=payload.files,
        query=payload.query,
        levels=payload.levels,
        start_at=start_at,
        end_at=end_at,
        recent_minutes=payload.recent_minutes,
        limit=payload.limit,
    )
    return JSONResponse({"items": [serialize_entry(item) for item in entries], "stats": stats})


@router.get("/api/stream")
async def stream(
    request: Request,
    files: list[str] = Query(default=[]),
    query: str = "",
    levels: list[str] = Query(default=[]),
    start_jalali: str = "",
    end_jalali: str = "",
    start_gregorian: str = "",
    end_gregorian: str = "",
    recent_minutes: int | None = Query(default=None, ge=1, le=10080),
    limit: int = Query(default=100, ge=1, le=MAX_RESULTS),
    username: str = Depends(require_user),
) -> StreamingResponse:
    del username

    async def event_generator():
        last_signature = ""
        while True:
            if await request.is_disconnected():
                break
            start_at = parse_gregorian_datetime(start_gregorian) or parse_jalali_datetime(start_jalali)
            end_at = parse_gregorian_datetime(end_gregorian) or parse_jalali_datetime(end_jalali, end_of_day=True)
            entries, stats = search_logs(
                files=files,
                query=query,
                levels=levels,
                start_at=start_at,
                end_at=end_at,
                recent_minutes=recent_minutes,
                limit=limit,
            )
            payload = {"items": [serialize_entry(item) for item in entries], "stats": stats}
            signature = json.dumps([item["id"] for item in payload["items"][:20]], separators=(",", ":"))
            if signature != last_signature:
                last_signature = signature
                yield f"event: logs\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            else:
                yield f"event: ping\ndata: {json.dumps({'ok': True})}\n\n"
            await asyncio.sleep(STREAM_INTERVAL_SECONDS)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
