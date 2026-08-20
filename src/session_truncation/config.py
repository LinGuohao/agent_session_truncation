from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Config:
    buffer_dir: Path
    output_dir: Path
    timezone_name: str
    env_file: Path | None


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ValueError(f"{path}:{number}: 配置行缺少 '='")
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"{path}:{number}: 配置键为空")
        values[key] = _unquote(value.strip())
    return values


def _find_env_file(explicit: str | None) -> Path | None:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"env 配置文件不存在：{path}")
        return path

    cwd_env = Path.cwd() / ".env"
    if cwd_env.is_file():
        return cwd_env.resolve()

    project_env = PROJECT_ROOT / ".env"
    if project_env.is_file():
        return project_env.resolve()
    return None


def _resolve_dir(raw: str, base_dir: Path) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def load_config(
    *,
    env_file: str | None = None,
    output_dir: str | None = None,
    timezone_name: str | None = None,
) -> Config:
    selected_env = _find_env_file(
        env_file or os.environ.get("SESSION_TRUNCATION_ENV_FILE")
    )
    file_values = _read_env_file(selected_env) if selected_env else {}
    base_dir = selected_env.parent if selected_env else PROJECT_ROOT

    def setting(name: str, default: str) -> str:
        return os.environ.get(name, file_values.get(name, default))

    buffer_raw = setting("SESSION_TRUNCATION_BUFFER_DIR", "./tmp")
    output_raw = output_dir or setting(
        "SESSION_TRUNCATION_OUTPUT_DIR", "~/Downloads"
    )
    tz_raw = timezone_name or setting("SESSION_TRUNCATION_TIMEZONE", "local")

    return Config(
        buffer_dir=_resolve_dir(buffer_raw, base_dir),
        output_dir=_resolve_dir(output_raw, base_dir),
        timezone_name=tz_raw.strip() or "local",
        env_file=selected_env,
    )
