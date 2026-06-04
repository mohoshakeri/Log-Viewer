import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("LOG_VIEWER_USERNAME", "test-admin")
os.environ.setdefault("LOG_VIEWER_PASSWORD", "test-password")
os.environ.setdefault("LOG_VIEWER_TOTP_SECRET", "JBSWY3DPEHPK3PXQ")
os.environ.setdefault("LOG_VIEWER_SESSION_SECRET", "test-session-secret-with-enough-entropy")

from fastapi import FastAPI

from main import create_app
from utils.jalali import format_jalali, parse_jalali_datetime
from utils.logs import list_log_files, iter_recent_lines, parse_line, read_log_context, search_logs
from utils.security import create_session, read_session


class AppFactoryTestCase(unittest.TestCase):
    def test_create_app_returns_fastapi_with_expected_routes(self) -> None:
        app: FastAPI = create_app()
        paths: set[str] = {route.path for route in app.routes}

        self.assertIsInstance(app, FastAPI)
        self.assertIn("/health", paths)
        self.assertIn("/api/logs", paths)
        self.assertIn("/api/log-context", paths)
        self.assertIn("/static", paths)


class JalaliDateTestCase(unittest.TestCase):
    def test_parse_and_format_jalali_datetime(self) -> None:
        parsed: datetime | None = parse_jalali_datetime("۱۴۰۳/۰۱/۰۱ 12:30:45")

        self.assertEqual(datetime(2024, 3, 20, 12, 30, 45), parsed)
        self.assertEqual("1403/01/01 12:30:45", format_jalali(parsed))

    def test_end_of_day_is_used_when_requested(self) -> None:
        parsed: datetime | None = parse_jalali_datetime("1403-01-01", end_of_day=True)

        self.assertEqual(datetime(2024, 3, 20, 23, 59, 59), parsed)


class LogParsingTestCase(unittest.TestCase):
    def test_parse_line_extracts_json_timestamp_level_and_message(self) -> None:
        raw: str = json.dumps(
            {
                "timestamp": "2024-03-20T12:30:45Z",
                "level": "warn",
                "message": "disk almost full",
            }
        )

        entry = parse_line("app.log", 7, raw)

        self.assertEqual("app.log:7", entry.id)
        self.assertEqual("WARNING", entry.level)
        self.assertEqual("disk almost full", entry.message)
        self.assertEqual(datetime(2024, 3, 20, 12, 30, 45), entry.timestamp)

    def test_parse_line_rejects_unknown_json_level(self) -> None:
        raw: str = json.dumps({"level": 'x" onclick="alert(1)', "message": "bad level"})

        entry = parse_line("app.log", 1, raw)

        self.assertEqual("TEXT", entry.level)

    def test_search_logs_filters_by_file_query_level_and_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir: Path = Path(temp_dir)
            log_path: Path = data_dir / "app.log"
            rows: list[dict[str, str]] = [
                {"timestamp": "2024-03-20T12:00:00", "level": "INFO", "message": "ready"},
                {"timestamp": "2024-03-20T12:05:00", "level": "ERROR", "message": "boom happened"},
                {"timestamp": "2024-03-20T12:10:00", "level": "ERROR", "message": "other failure"},
            ]
            log_path.write_text("\n".join(json.dumps(row) for row in rows))

            with patch("utils.logs.DATA_DIR", data_dir):
                entries, stats = search_logs(files=["app.log"], query="boom", levels=["ERROR"], limit=10)

        self.assertEqual(1, len(entries))
        self.assertEqual("boom happened", entries[0].message)
        self.assertEqual(2, entries[0].line_number)
        self.assertEqual({"scanned": 3, "matched": 1, "returned": 1, "files": 1}, stats)

    def test_iter_recent_lines_uses_real_file_line_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path: Path = Path(temp_dir) / "app.log"
            log_path.write_text("\n".join("line {}".format(index) for index in range(1, 11)))

            lines = list(iter_recent_lines(log_path, 3))

        self.assertEqual([(8, "line 8"), (9, "line 9"), (10, "line 10")], lines)

    def test_read_log_context_returns_lines_around_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir: Path = Path(temp_dir)
            log_path: Path = data_dir / "app.log"
            log_path.write_text("\n".join("line {}".format(index) for index in range(1, 8)))

            with patch("utils.logs.DATA_DIR", data_dir):
                context = read_log_context("app.log", 4, context_lines=2)

        self.assertEqual("app.log", context["file"])
        self.assertEqual(2, context["start_line"])
        self.assertEqual(6, context["end_line"])
        self.assertEqual([2, 3, 4, 5, 6], [item["line"] for item in context["lines"]])
        self.assertEqual([False, False, True, False, False], [item["target"] for item in context["lines"]])

    def test_symlink_log_file_is_not_listed_or_read(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir: Path = Path(temp_dir) / "data"
            outside_dir: Path = Path(temp_dir) / "outside"
            data_dir.mkdir()
            outside_dir.mkdir()
            (data_dir / "app.log").write_text("safe")
            secret_path: Path = outside_dir / "secret.log"
            secret_path.write_text("secret")
            (data_dir / "secret.log").symlink_to(secret_path)

            with patch("utils.logs.DATA_DIR", data_dir):
                files = list_log_files()
                entries, stats = search_logs(files=["secret.log"], query="", levels=[], limit=10)

        self.assertEqual(["app.log"], [item.key for item in files])
        self.assertEqual([], entries)
        self.assertEqual(0, stats["files"])


class SessionTestCase(unittest.TestCase):
    def test_created_session_can_be_read_and_tampering_is_rejected(self) -> None:
        token: str = create_session("test-admin")
        payload = read_session(token)

        self.assertIsNotNone(payload)
        self.assertEqual("test-admin", payload["u"])
        self.assertIsNone(read_session("{}.broken".format(token)))


if __name__ == "__main__":
    unittest.main()
