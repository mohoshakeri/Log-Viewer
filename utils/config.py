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
LOGO_URL: str = os.getenv("LOG_VIEWER_LOGO_URL", "/static/logo.png").strip()
FAVICON_URL: str = os.getenv("LOG_VIEWER_FAVICON_URL", "/static/favicon.ico").strip()
CLIENT_API_TIMEOUT_SECONDS: int = int(os.getenv("LOG_VIEWER_CLIENT_API_TIMEOUT_SECONDS", "180"))
SERVER_KEEP_ALIVE_SECONDS: int = int(os.getenv("LOG_VIEWER_SERVER_KEEP_ALIVE_SECONDS", "120"))

if not CORS_ALLOWEDS:
    cors_defaults: set[str] = {
        BASE_URL,
        BASE_URL.replace("localhost", "127.0.0.1"),
        BASE_URL.replace("127.0.0.1", "localhost"),
    }
    CORS_ALLOWEDS = sorted(cors_defaults)

# ---------- Security Settings ----------
DEFAULT_AUTH_USERNAME = "admin"
DEFAULT_AUTH_PASSWORD = "1234"
DEFAULT_TOTP_SECRET = "JBSWY3DPEHPK3PXP"
DEFAULT_SESSION_SECRET = "pAQ!_Q4ZDy%2M4wMrQBXar_%5hFm&nUg+qT%w4-t"
PLACEHOLDER_AUTH_PASSWORD = "change-me"
PLACEHOLDER_SESSION_SECRET = "change-me-to-a-long-random-secret"

AUTH_USERNAME: str = os.getenv("LOG_VIEWER_USERNAME", "admin").strip()
AUTH_PASSWORD: str = os.getenv("LOG_VIEWER_PASSWORD", "1234").strip()
TOTP_SECRET: str = os.getenv("LOG_VIEWER_TOTP_SECRET", "JBSWY3DPEHPK3PXP").replace(" ", "").strip()
SESSION_SECRET: str = os.getenv("LOG_VIEWER_SESSION_SECRET", "pAQ!_Q4ZDy%2M4wMrQBXar_%5hFm&nUg+qT%w4-t").strip()
SESSION_COOKIE: str = os.getenv("LOG_VIEWER_SESSION_COOKIE", "slv_session").strip()
SESSION_TTL_SECONDS: int = int(os.getenv("LOG_VIEWER_SESSION_TTL_SECONDS", str(8 * 60 * 60)))
COOKIE_SECURE: bool = os.getenv("LOG_VIEWER_COOKIE_SECURE", "NO").upper() == "YES"
ALLOW_INSECURE_DEFAULTS: bool = os.getenv("LOG_VIEWER_ALLOW_INSECURE_DEFAULTS", "NO").upper() == "YES"
LOGIN_RATE_LIMIT_ATTEMPTS: int = int(os.getenv("LOG_VIEWER_LOGIN_RATE_LIMIT_ATTEMPTS", "5"))
LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("LOG_VIEWER_LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300"))
LOGIN_RATE_LIMIT_BLOCK_SECONDS: int = int(os.getenv("LOG_VIEWER_LOGIN_RATE_LIMIT_BLOCK_SECONDS", "900"))

# ---------- Query Limits ----------
MAX_RESULTS: int = int(os.getenv("LOG_VIEWER_MAX_RESULTS", "500"))
MAX_SCAN_LINES: int = int(os.getenv("LOG_VIEWER_MAX_SCAN_LINES", "12000"))
MAX_LINE_LENGTH: int = int(os.getenv("LOG_VIEWER_MAX_LINE_LENGTH", "20000"))
LOG_CONTEXT_LINES: int = int(os.getenv("LOG_VIEWER_CONTEXT_LINES", "30"))
STREAM_INTERVAL_SECONDS: int = int(os.getenv("LOG_VIEWER_STREAM_INTERVAL_SECONDS", "5"))
MAX_SELECTED_FILES: int = int(os.getenv("LOG_VIEWER_MAX_SELECTED_FILES", "50"))
MAX_CONTEXT_TARGET_LINE: int = int(os.getenv("LOG_VIEWER_MAX_CONTEXT_TARGET_LINE", "1000000"))
MAX_LOG_FILE_BYTES: int = int(os.getenv("LOG_VIEWER_MAX_LOG_FILE_BYTES", str(512 * 1024 * 1024)))


def validate_security_config() -> None:
    insecure_defaults = [
        ("LOG_VIEWER_USERNAME", AUTH_USERNAME, DEFAULT_AUTH_USERNAME),
        ("LOG_VIEWER_PASSWORD", AUTH_PASSWORD, DEFAULT_AUTH_PASSWORD),
        ("LOG_VIEWER_TOTP_SECRET", TOTP_SECRET, DEFAULT_TOTP_SECRET),
        ("LOG_VIEWER_SESSION_SECRET", SESSION_SECRET, DEFAULT_SESSION_SECRET),
        ("LOG_VIEWER_PASSWORD", AUTH_PASSWORD, PLACEHOLDER_AUTH_PASSWORD),
        ("LOG_VIEWER_SESSION_SECRET", SESSION_SECRET, PLACEHOLDER_SESSION_SECRET),
    ]
    weak = [name for name, value, default in insecure_defaults if value == default]
    if weak and not ALLOW_INSECURE_DEFAULTS and not DEBUG:
        joined = ", ".join(weak)
        raise RuntimeError(
            "Refusing to start with insecure default authentication settings: {}. "
            "Set strong environment values, or set LOG_VIEWER_ALLOW_INSECURE_DEFAULTS=YES for local development.".format(
                joined
            )
        )
