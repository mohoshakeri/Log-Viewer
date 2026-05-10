# Simple Log Viewer

FastAPI log viewer for files under `data/` with Jalali and Gregorian date range filters, recent-minute filters, full-text search, colorful log levels, and 5-second live updates over Server-Sent Events.

![img.png](static/img.png)

## Features

- Secure login with username, password, and TOTP.
- TOTP secret, password, and session secret are read from environment variables.
- Reads nested log files from `data/` without exposing filesystem paths.
- Supports JSON line logs and common nginx access/error logs.
- Jalali date picker with time, plus Gregorian `datetime-local` range filters.
- Pretty syntax-colored JSON details when a log line can be parsed as JSON.
- Recent minutes shortcut, full-text search, level filters, file filters, and result limits.
- Responsive RTL UI with Vazirmatn FD NL loaded from ArvanCloud.
- Optional logo and favicon URLs from environment variables.
- Secure headers, HttpOnly same-site session cookie, signed session token, and path traversal protection.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set strong values:

```env
LOG_VIEWER_USERNAME=admin
LOG_VIEWER_PASSWORD=use-a-strong-password
LOG_VIEWER_TOTP_SECRET=BASE32_TOTP_SECRET
LOG_VIEWER_SESSION_SECRET=use-a-long-random-secret
LOG_VIEWER_LOGO_URL=https://example.com/logo.png
LOG_VIEWER_FAVICON_URL=https://example.com/favicon.ico
```

`LOG_VIEWER_TOTP_SECRET` must be a Base32 secret compatible with authenticator apps.

For production behind HTTPS, also set:

```env
LOG_VIEWER_COOKIE_SECURE=YES
DEBUG=NO
```

## Run

```bash
uvicorn main:app --host 0.0.0.0 --port 8989
```

Then open:

```text
http://localhost:8989
```

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `PORT` | `8989` | App port when running `python main.py`. |
| `BASE_URL` | `http://localhost:8989` | Base URL used for CORS defaults. |
| `LOG_DATA_DIR` | `data` | Directory that contains log files. |
| `LOG_VIEWER_USERNAME` | `admin` | Login username. |
| `LOG_VIEWER_PASSWORD` | empty | Login password. Must be set. |
| `LOG_VIEWER_TOTP_SECRET` | empty | Base32 TOTP secret. Must be set. |
| `LOG_VIEWER_SESSION_SECRET` | empty | HMAC session signing secret. Must be set. |
| `LOG_VIEWER_COOKIE_SECURE` | `NO` | Set to `YES` on HTTPS. |
| `LOG_VIEWER_SESSION_TTL_SECONDS` | `28800` | Session lifetime. |
| `LOG_VIEWER_LOGO_URL` | empty | Optional logo URL shown in the header. |
| `LOG_VIEWER_FAVICON_URL` | empty | Optional favicon URL used by the page. |
| `LOG_VIEWER_MAX_RESULTS` | `500` | Maximum returned results per query. |
| `LOG_VIEWER_MAX_SCAN_LINES` | `12000` | Recent lines scanned per file. |

## API

- `POST /api/login`
- `POST /api/logout`
- `GET /api/me`
- `GET /api/files`
- `POST /api/logs`
- `GET /api/stream`

All log APIs require the authenticated session cookie.

## Notes

The viewer scans the most recent `LOG_VIEWER_MAX_SCAN_LINES` lines per selected file to stay responsive on large logs. Increase that value only if the server has enough CPU and memory for wider searches.
