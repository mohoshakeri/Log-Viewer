import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None


if load_dotenv:
    load_dotenv()

# ---------- Project Paths ----------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = PROJECT_ROOT / "static"
DATA_DIR = (PROJECT_ROOT / os.getenv("LOG_DATA_DIR", "data")).resolve()

# ---------- Runtime Settings ----------
DEBUG = os.getenv("DEBUG", "NO").upper() == "YES"
PORT = int(os.getenv("PORT", "8989"))
BASE_URL = os.getenv("BASE_URL", f"http://localhost:{PORT}").rstrip("/")
CORS_ALLOWEDS = [item.strip() for item in os.getenv("CORS_ALLOWEDS", "").split(",") if item.strip()]

if not CORS_ALLOWEDS:
    cors_defaults = {
        BASE_URL,
        BASE_URL.replace("localhost", "127.0.0.1"),
        BASE_URL.replace("127.0.0.1", "localhost"),
    }
    CORS_ALLOWEDS = sorted(cors_defaults)

# ---------- Security Settings ----------
AUTH_USERNAME = os.getenv("LOG_VIEWER_USERNAME", "admin").strip()
AUTH_PASSWORD = os.getenv("LOG_VIEWER_PASSWORD", "1234").strip()
TOTP_SECRET = os.getenv("LOG_VIEWER_TOTP_SECRET", "JBSWY3DPEHPK3PXP").replace(" ", "").strip()
SESSION_SECRET = os.getenv("LOG_VIEWER_SESSION_SECRET", "pAQ!_Q4ZDy%2M4wMrQBXar_%5hFm&nUg+qT%w4-t").strip()
SESSION_COOKIE = os.getenv("LOG_VIEWER_SESSION_COOKIE", "slv_session").strip()
SESSION_TTL_SECONDS = int(os.getenv("LOG_VIEWER_SESSION_TTL_SECONDS", str(8 * 60 * 60)))
COOKIE_SECURE = os.getenv("LOG_VIEWER_COOKIE_SECURE", "NO").upper() == "YES"

# ---------- Query Limits ----------
MAX_RESULTS = int(os.getenv("LOG_VIEWER_MAX_RESULTS", "500"))
MAX_SCAN_LINES = int(os.getenv("LOG_VIEWER_MAX_SCAN_LINES", "12000"))
MAX_LINE_LENGTH = int(os.getenv("LOG_VIEWER_MAX_LINE_LENGTH", "20000"))
STREAM_INTERVAL_SECONDS = 5
