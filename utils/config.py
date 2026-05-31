import os
from pathlib import Path
from typing import Callable

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv: Callable[[], bool] | None = None


if load_dotenv:
    load_dotenv()

# ---------- Project Paths ----------
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
STATIC_DIR: Path = PROJECT_ROOT / "static"
DATA_DIR: Path = (PROJECT_ROOT / os.getenv("LOG_DATA_DIR", "data")).resolve()

# ---------- Runtime Settings ----------
DEBUG: bool = os.getenv("DEBUG", "NO").upper() == "YES"
PORT: int = int(os.getenv("PORT", "8989"))
BASE_URL: str = os.getenv("BASE_URL", "http://localhost:{}".format(PORT)).rstrip("/")
CORS_ALLOWEDS: list[str] = [item.strip() for item in os.getenv("CORS_ALLOWEDS", "").split(",") if item.strip()]
LOGO_URL: str = os.getenv("LOG_VIEWER_LOGO_URL", "").strip()
FAVICON_URL: str = os.getenv("LOG_VIEWER_FAVICON_URL", "").strip()

if not CORS_ALLOWEDS:
    cors_defaults: set[str] = {
        BASE_URL,
        BASE_URL.replace("localhost", "127.0.0.1"),
        BASE_URL.replace("127.0.0.1", "localhost"),
    }
    CORS_ALLOWEDS = sorted(cors_defaults)

# ---------- Security Settings ----------
AUTH_USERNAME: str = os.getenv("LOG_VIEWER_USERNAME", "admin").strip()
AUTH_PASSWORD: str = os.getenv("LOG_VIEWER_PASSWORD", "1234").strip()
TOTP_SECRET: str = os.getenv("LOG_VIEWER_TOTP_SECRET", "JBSWY3DPEHPK3PXP").replace(" ", "").strip()
SESSION_SECRET: str = os.getenv("LOG_VIEWER_SESSION_SECRET", "pAQ!_Q4ZDy%2M4wMrQBXar_%5hFm&nUg+qT%w4-t").strip()
SESSION_COOKIE: str = os.getenv("LOG_VIEWER_SESSION_COOKIE", "slv_session").strip()
SESSION_TTL_SECONDS: int = int(os.getenv("LOG_VIEWER_SESSION_TTL_SECONDS", str(8 * 60 * 60)))
COOKIE_SECURE: bool = os.getenv("LOG_VIEWER_COOKIE_SECURE", "NO").upper() == "YES"

# ---------- Query Limits ----------
MAX_RESULTS: int = int(os.getenv("LOG_VIEWER_MAX_RESULTS", "500"))
MAX_SCAN_LINES: int = int(os.getenv("LOG_VIEWER_MAX_SCAN_LINES", "12000"))
MAX_LINE_LENGTH: int = int(os.getenv("LOG_VIEWER_MAX_LINE_LENGTH", "20000"))
STREAM_INTERVAL_SECONDS: int = 5
