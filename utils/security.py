import base64
import hashlib
import hmac
import json
import secrets
import struct
import time
from typing import Any

from fastapi import HTTPException, Request, Response, status

from utils.config import (
    AUTH_PASSWORD,
    AUTH_USERNAME,
    COOKIE_SECURE,
    LOGIN_RATE_LIMIT_ATTEMPTS,
    LOGIN_RATE_LIMIT_BLOCK_SECONDS,
    LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    SESSION_COOKIE,
    SESSION_SECRET,
    SESSION_TTL_SECONDS,
    TOTP_SECRET,
)


_login_attempts: dict[str, list[float]] = {}
_login_blocked_until: dict[str, float] = {}


# ---------- TOTP Verification ----------
def _base32_decode(secret: str) -> bytes:
    padding = "=" * ((8 - len(secret) % 8) % 8)
    try:
        return base64.b32decode((secret + padding).upper(), casefold=True)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Invalid TOTP configuration.") from exc


def _totp_code(secret: str, counter: int, digits: int = 6) -> str:
    key = _base32_decode(secret)
    message = struct.pack(">Q", counter)
    digest = hmac.new(key, message, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(code_int % (10**digits)).zfill(digits)


def verify_totp(code: str, window: int = 1) -> bool:
    current_counter = int(time.time() // 30)
    normalized = "".join(char for char in code if char.isdigit())
    if len(normalized) != 6 or not TOTP_SECRET:
        return False

    for drift in range(-window, window + 1):
        expected = _totp_code(TOTP_SECRET, current_counter + drift)
        if secrets.compare_digest(expected, normalized):
            return True
    return False


# ---------- Session Tokens ----------
def auth_is_configured() -> bool:
    return bool(AUTH_USERNAME and AUTH_PASSWORD and TOTP_SECRET and SESSION_SECRET)


def _b64_encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _b64_decode(payload: str) -> bytes:
    padding = "=" * ((4 - len(payload) % 4) % 4)
    return base64.urlsafe_b64decode(payload + padding)


def create_session(username: str) -> str:
    issued_at = int(time.time())
    nonce = secrets.token_urlsafe(16)
    payload: dict[str, str | int] = {"u": username, "iat": issued_at, "n": nonce}
    body = _b64_encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = hmac.new(SESSION_SECRET.encode(), body.encode(), hashlib.sha256).digest()
    return "{}.{}".format(body, _b64_encode(signature))


def read_session(token: str) -> dict[str, Any] | None:
    if "." not in token or not SESSION_SECRET:
        return None
    body, signature = token.rsplit(".", 1)
    expected = _b64_encode(hmac.new(SESSION_SECRET.encode(), body.encode(), hashlib.sha256).digest())
    if not secrets.compare_digest(expected, signature):
        return None
    try:
        payload = json.loads(_b64_decode(body))
    except Exception:
        return None
    if int(time.time()) - int(payload.get("iat", 0)) > SESSION_TTL_SECONDS:
        return None
    if payload.get("u") != AUTH_USERNAME:
        return None
    return payload


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE, path="/")


def require_user(request: Request) -> str:
    token = request.cookies.get(SESSION_COOKIE, "")
    payload = read_session(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return str(payload["u"])


def validate_login(username: str, password: str, totp_code: str) -> bool:
    if not auth_is_configured():
        raise HTTPException(status_code=500, detail="Authentication environment is not configured.")
    return (
        secrets.compare_digest(username, AUTH_USERNAME)
        and secrets.compare_digest(password, AUTH_PASSWORD)
        and verify_totp(totp_code)
    )


def login_rate_key(request: Request, username: str) -> str:
    client_host = request.client.host if request.client else "unknown"
    return "{}:{}".format(client_host, username.strip().casefold())


def check_login_rate_limit(key: str) -> None:
    now = time.monotonic()
    blocked_until = _login_blocked_until.get(key, 0)
    if blocked_until > now:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts.")
    if blocked_until:
        _login_blocked_until.pop(key, None)


def record_login_failure(key: str) -> None:
    now = time.monotonic()
    window_start = now - LOGIN_RATE_LIMIT_WINDOW_SECONDS
    attempts = [item for item in _login_attempts.get(key, []) if item >= window_start]
    attempts.append(now)
    if len(attempts) >= LOGIN_RATE_LIMIT_ATTEMPTS:
        _login_blocked_until[key] = now + LOGIN_RATE_LIMIT_BLOCK_SECONDS
        _login_attempts.pop(key, None)
        return
    _login_attempts[key] = attempts


def record_login_success(key: str) -> None:
    _login_attempts.pop(key, None)
    _login_blocked_until.pop(key, None)
