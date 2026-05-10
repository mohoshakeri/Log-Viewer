import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from utils.config import DATA_DIR, MAX_LINE_LENGTH, MAX_RESULTS, MAX_SCAN_LINES
from utils.jalali import format_jalali


LEVEL_RE = re.compile(r"\b(CRITICAL|FATAL|ERROR|WARNING|WARN|INFO|DEBUG|TRACE)\b", re.IGNORECASE)
NGINX_RE = re.compile(r"\[(?P<date>\d{1,2}/[A-Za-z]{3}/\d{4}:\d{2}:\d{2}:\d{2} [+-]\d{4})\]")
ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}[T ][\d:.]+(?:Z|[+-]\d{2}:?\d{2})?")


@dataclass
class LogFile:
    key: str
    path: Path
    size: int
    modified_at: datetime


@dataclass
class LogEntry:
    id: str
    file: str
    line_number: int
    timestamp: datetime | None
    level: str
    message: str
    raw: str
    meta: dict


# ---------- File Discovery ----------
def list_log_files() -> list[LogFile]:
    DATA_DIR.mkdir(exist_ok=True)
    files: list[LogFile] = []
    for path in DATA_DIR.rglob("*"):
        if not path.is_file():
            continue
        if ".log" not in path.name and not path.name.endswith((".txt", ".json")):
            continue
        stat = path.stat()
        files.append(
            LogFile(
                key=path.relative_to(DATA_DIR).as_posix(),
                path=path,
                size=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime),
            )
        )
    return sorted(files, key=lambda item: item.key)


def resolve_log_file(key: str) -> Path:
    cleaned = key.strip().lstrip("/")
    candidate = (DATA_DIR / cleaned).resolve()
    if DATA_DIR not in candidate.parents or not candidate.is_file():
        raise ValueError("Invalid log file.")
    return candidate


# ---------- Date Parsing ----------
def parse_timestamp(raw: str, parsed_json: dict | None = None) -> datetime | None:
    values: list[str] = []
    if parsed_json:
        for key in ("@timestamp", "timestamp", "time", "datetime", "created_at"):
            value = parsed_json.get(key)
            if isinstance(value, str):
                values.append(value)

    nginx_match = NGINX_RE.search(raw)
    if nginx_match:
        values.append(nginx_match.group("date"))

    iso_match = ISO_RE.search(raw)
    if iso_match:
        values.append(iso_match.group(0))

    for value in values:
        normalized = value.replace("Z", "+00:00")
        try:
            if "/" in normalized and ":" in normalized and normalized[2] == "/":
                return datetime.strptime(normalized, "%d/%b/%Y:%H:%M:%S %z").astimezone(timezone.utc).replace(tzinfo=None)
            dt = datetime.fromisoformat(normalized)
            if dt.tzinfo:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except Exception:
            continue
    return None


def detect_level(raw: str, parsed_json: dict | None = None) -> str:
    if parsed_json:
        value = parsed_json.get("level") or parsed_json.get("levelname") or parsed_json.get("severity")
        if isinstance(value, str) and value.strip():
            return value.strip().upper().replace("WARN", "WARNING")
    match = LEVEL_RE.search(raw)
    if not match:
        return "TEXT"
    return match.group(1).upper().replace("WARN", "WARNING")


# ---------- Entry Parsing ----------
def parse_line(file_key: str, line_number: int, raw: str) -> LogEntry:
    trimmed = raw.rstrip("\n")
    parsed_json = None
    meta: dict = {}
    message = trimmed

    try:
        loaded = json.loads(trimmed)
        if isinstance(loaded, dict):
            parsed_json = loaded
            meta = loaded
            message_value = loaded.get("message") or loaded.get("msg")
            extra = loaded.get("extra") if isinstance(loaded.get("extra"), dict) else {}
            if not message_value and extra:
                message_value = extra.get("message")
            message = str(message_value) if message_value else json.dumps(loaded, ensure_ascii=False)
    except json.JSONDecodeError:
        pass

    timestamp = parse_timestamp(trimmed, parsed_json)
    level = detect_level(trimmed, parsed_json)
    return LogEntry(
        id=f"{file_key}:{line_number}",
        file=file_key,
        line_number=line_number,
        timestamp=timestamp,
        level=level,
        message=message[:MAX_LINE_LENGTH],
        raw=trimmed[:MAX_LINE_LENGTH],
        meta=meta,
    )


def iter_recent_lines(path: Path, max_lines: int) -> Iterable[tuple[int, str]]:
    chunk_size = 64 * 1024
    data = bytearray()
    newline_count = 0
    with path.open("rb") as handle:
        handle.seek(0, 2)
        position = handle.tell()
        while position > 0 and newline_count <= max_lines:
            read_size = min(chunk_size, position)
            position -= read_size
            handle.seek(position)
            chunk = handle.read(read_size)
            data[:0] = chunk
            newline_count += chunk.count(b"\n")

    decoded = bytes(data).decode("utf-8", errors="replace").splitlines()
    lines = decoded[-max_lines:]
    for index, line in enumerate(lines, start=1):
        yield index, line


# ---------- Query Engine ----------
def search_logs(
    files: list[str] | None = None,
    query: str = "",
    levels: list[str] | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    recent_minutes: int | None = None,
    limit: int = MAX_RESULTS,
) -> tuple[list[LogEntry], dict]:
    allowed_files = {item.key: item for item in list_log_files()}
    selected_keys = files or list(allowed_files.keys())
    selected = [allowed_files[key] for key in selected_keys if key in allowed_files]
    level_set = {level.upper() for level in (levels or []) if level}
    needles = [part.casefold() for part in query.split() if part.strip()]
    if recent_minutes:
        start_at = datetime.utcnow() - timedelta(minutes=recent_minutes)
        end_at = None

    entries: list[LogEntry] = []
    scanned = 0
    for item in selected:
        for line_number, line in iter_recent_lines(item.path, MAX_SCAN_LINES):
            scanned += 1
            entry = parse_line(item.key, line_number, line)
            if level_set and entry.level not in level_set:
                continue
            if start_at and (not entry.timestamp or entry.timestamp < start_at):
                continue
            if end_at and (not entry.timestamp or entry.timestamp > end_at):
                continue
            haystack = f"{entry.raw} {entry.file}".casefold()
            if needles and not all(needle in haystack for needle in needles):
                continue
            entries.append(entry)

    entries.sort(key=lambda item: item.timestamp or datetime.min, reverse=True)
    limited = entries[: max(1, min(limit, MAX_RESULTS))]
    stats = {"scanned": scanned, "matched": len(entries), "returned": len(limited), "files": len(selected)}
    return limited, stats


def serialize_file(item: LogFile) -> dict:
    return {
        "key": item.key,
        "size": item.size,
        "modified_at": item.modified_at.isoformat(timespec="seconds"),
        "modified_jalali": format_jalali(item.modified_at),
    }


def serialize_entry(entry: LogEntry) -> dict:
    return {
        "id": entry.id,
        "file": entry.file,
        "line": entry.line_number,
        "timestamp": entry.timestamp.isoformat(timespec="seconds") if entry.timestamp else None,
        "jalali": format_jalali(entry.timestamp),
        "level": entry.level,
        "raw": entry.raw,
        "meta": entry.meta,
    }
