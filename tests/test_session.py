from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import time
import unittest

from session_truncation.config import load_config
from session_truncation.cli import build_parser
from session_truncation.timeparse import parse_cutoff
from session_truncation.truncate import truncate_history


class TimeParsingTests(unittest.TestCase):
    def test_cc_switch_display_time_uses_system_local_timezone(self) -> None:
        if not hasattr(time, "tzset"):
            self.skipTest("系统不支持 tzset")
        previous = os.environ.get("TZ")
        try:
            os.environ["TZ"] = "Europe/Brussels"
            time.tzset()
            parsed = parse_cutoff("8/20/2026, 6:09:25 PM", "local")
            self.assertEqual(
                parsed,
                datetime(2026, 8, 20, 16, 9, 25, tzinfo=timezone.utc),
            )
        finally:
            if previous is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = previous
            time.tzset()

    def test_explicit_iana_timezone(self) -> None:
        parsed = parse_cutoff("2026-08-20 18:09:25", "Europe/Brussels")
        self.assertEqual(
            parsed,
            datetime(2026, 8, 20, 16, 9, 25, tzinfo=timezone.utc),
        )


class CliParsingTests(unittest.TestCase):
    def test_unquoted_display_time_is_accepted(self) -> None:
        args = build_parser().parse_args(
            ["history.jsonl", "8/20/2026,", "6:33:11", "PM"]
        )
        self.assertEqual(" ".join(args.time), "8/20/2026, 6:33:11 PM")


class TruncationTests(unittest.TestCase):
    def test_preserves_source_and_file_order_while_filtering_each_record(self) -> None:
        with tempfile.TemporaryDirectory() as root_name:
            root = Path(root_name)
            source = root / "history.jsonl"
            records = [
                {"timestamp": "2026-08-20T16:09:24.999Z", "id": "before"},
                {"timestamp": "2026-08-20T16:09:25.187Z", "id": "first"},
                {"timestamp": "2026-08-20T16:09:31Z", "id": "second"},
                {"timestamp": "2026-08-20T15:00:00Z", "id": "late-old-row"},
                {"type": "custom-title", "id": "no-time"},
                {"timestamp": 1_787_242_166, "id": "numeric-seconds"},
            ]
            original = b"".join(
                json.dumps(record).encode("utf-8") + b"\n" for record in records
            )
            source.write_bytes(original)
            buffer_dir = root / "buffer"
            output_dir = root / "output"

            result = truncate_history(
                source,
                datetime(2026, 8, 20, 16, 9, 25, tzinfo=timezone.utc),
                buffer_dir=buffer_dir,
                output_dir=output_dir,
                timezone_name="Europe/Brussels",
            )

            output_records = [json.loads(line) for line in result.output.read_text().splitlines()]
            self.assertEqual(
                [record["id"] for record in output_records],
                ["first", "second", "numeric-seconds"],
            )
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(list(buffer_dir.iterdir()), [])
            self.assertEqual(result.total_lines, 6)
            self.assertEqual(result.selected_lines, 3)
            self.assertEqual(result.missing_timestamp_lines, 1)

    def test_invalid_json_is_skipped_and_buffer_is_cleaned(self) -> None:
        with tempfile.TemporaryDirectory() as root_name:
            root = Path(root_name)
            source = root / "history.jsonl"
            source.write_bytes(
                b"not-json\n"
                b'{"timestamp":"2026-08-20T16:09:25Z","ok":true}\n'
            )
            result = truncate_history(
                source,
                datetime(2026, 8, 20, 16, 9, 25, tzinfo=timezone.utc),
                buffer_dir=root / "buffer",
                output_dir=root / "output",
                timezone_name="UTC",
            )
            self.assertEqual(result.invalid_json_lines, 1)
            self.assertEqual(result.selected_lines, 1)
            self.assertEqual(list((root / "buffer").iterdir()), [])

    def test_existing_output_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as root_name:
            root = Path(root_name)
            source = root / "history.jsonl"
            source.write_text('{"timestamp":"2026-08-20T16:09:25Z"}\n')
            kwargs = {
                "buffer_dir": root / "buffer",
                "output_dir": root / "output",
                "timezone_name": "UTC",
            }
            cutoff = datetime(2026, 8, 20, 16, 9, 25, tzinfo=timezone.utc)
            first = truncate_history(source, cutoff, **kwargs)
            second = truncate_history(source, cutoff, **kwargs)
            self.assertNotEqual(first.output, second.output)
            self.assertTrue(first.output.is_file())
            self.assertTrue(second.output.is_file())


class ConfigTests(unittest.TestCase):
    def test_relative_paths_are_resolved_from_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as root_name:
            root = Path(root_name)
            env_file = root / "custom.env"
            env_file.write_text(
                "SESSION_TRUNCATION_BUFFER_DIR=cache\n"
                "SESSION_TRUNCATION_OUTPUT_DIR=generated\n"
                "SESSION_TRUNCATION_TIMEZONE=UTC\n"
            )
            config = load_config(env_file=str(env_file))
            self.assertEqual(config.buffer_dir, (root / "cache").resolve())
            self.assertEqual(config.output_dir, (root / "generated").resolve())
            self.assertEqual(config.timezone_name, "UTC")


if __name__ == "__main__":
    unittest.main()
