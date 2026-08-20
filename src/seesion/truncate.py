from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import tempfile

from .timeparse import cutoff_label, parse_record_timestamp


@dataclass(frozen=True)
class TruncationResult:
    source: Path
    output: Path
    total_lines: int
    selected_lines: int
    missing_timestamp_lines: int
    invalid_json_lines: int


def _available_output_path(output_dir: Path, stem: str, label: str) -> Path:
    base = output_dir / f"{stem}_from_{label}.jsonl"
    if not base.exists():
        return base
    suffix = 2
    while True:
        candidate = output_dir / f"{stem}_from_{label}_{suffix}.jsonl"
        if not candidate.exists():
            return candidate
        suffix += 1


def truncate_history(
    source: Path,
    cutoff_utc: datetime,
    *,
    buffer_dir: Path,
    output_dir: Path,
    timezone_name: str,
) -> TruncationResult:
    source = source.expanduser().resolve()
    if not source.is_file():
        raise ValueError(f"会话历史文件不存在：{source}")

    buffer_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    file_descriptor, buffer_name = tempfile.mkstemp(
        prefix=f"{source.stem}-",
        suffix=".jsonl",
        dir=buffer_dir,
    )
    os.close(file_descriptor)
    buffer_path = Path(buffer_name)
    partial_path: Path | None = None

    try:
        shutil.copy2(source, buffer_path)
        label = cutoff_label(cutoff_utc, timezone_name)
        output_path = _available_output_path(output_dir, source.stem, label)

        partial_descriptor, partial_name = tempfile.mkstemp(
            prefix=f".{output_path.name}.",
            suffix=".part",
            dir=output_dir,
        )
        partial_path = Path(partial_name)

        total = 0
        selected = 0
        missing_timestamp = 0
        invalid_json = 0
        with open(partial_descriptor, "wb", closefd=True) as destination:
            with buffer_path.open("rb") as history:
                for raw_line in history:
                    total += 1
                    try:
                        record = json.loads(raw_line)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        invalid_json += 1
                        continue

                    if not isinstance(record, dict) or "timestamp" not in record:
                        missing_timestamp += 1
                        continue
                    timestamp = parse_record_timestamp(record["timestamp"])
                    if timestamp is None:
                        missing_timestamp += 1
                        continue
                    if timestamp >= cutoff_utc:
                        destination.write(raw_line)
                        selected += 1
            destination.flush()
            os.fsync(destination.fileno())

        os.replace(partial_path, output_path)
        partial_path = None
        return TruncationResult(
            source=source,
            output=output_path,
            total_lines=total,
            selected_lines=selected,
            missing_timestamp_lines=missing_timestamp,
            invalid_json_lines=invalid_json,
        )
    finally:
        buffer_path.unlink(missing_ok=True)
        if partial_path is not None:
            partial_path.unlink(missing_ok=True)
