from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DISPLAY_FORMATS = (
    "%m/%d/%Y, %I:%M:%S %p",
    "%m/%d/%Y %I:%M:%S %p",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)


def _parse_datetime_text(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith(("Z", "z")):
        normalized = normalized[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        pass

    for pattern in DISPLAY_FORMATS:
        try:
            return datetime.strptime(value.strip(), pattern)
        except ValueError:
            continue
    raise ValueError(
        "无法解析时间。示例：'8/20/2026, 6:09:25 PM'、"
        "'2026-08-20 18:09:25' 或带时区的 ISO 8601 时间"
    )


def parse_cutoff(value: str, timezone_name: str) -> datetime:
    parsed = _parse_datetime_text(value)
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc)

    if timezone_name.lower() == "local":
        # 与浏览器 Date.toLocaleString() 的逆向语义一致：无时区输入按系统本地时间解释。
        return parsed.astimezone(timezone.utc)

    try:
        local_zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise ValueError(f"未知时区：{timezone_name}") from error
    return parsed.replace(tzinfo=local_zone).astimezone(timezone.utc)


def parse_record_timestamp(value: object) -> datetime | None:
    # 与 cc-switch 一致：数字大于 1e12 时视为毫秒，否则视为秒。
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        seconds = float(value) / 1000 if value > 1_000_000_000_000 else float(value)
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if not isinstance(value, str):
        return None

    normalized = value.strip()
    if normalized.endswith(("Z", "z")):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def cutoff_label(cutoff_utc: datetime, timezone_name: str) -> str:
    if timezone_name.lower() == "local":
        local = cutoff_utc.astimezone()
    else:
        try:
            local = cutoff_utc.astimezone(ZoneInfo(timezone_name))
        except ZoneInfoNotFoundError as error:
            raise ValueError(f"未知时区：{timezone_name}") from error
    return local.strftime("%Y%m%dT%H%M%S%z")
