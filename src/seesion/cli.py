from __future__ import annotations

import argparse
from pathlib import Path
import sys

from . import __version__
from .config import load_config
from .timeparse import parse_cutoff
from .truncate import truncate_history


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="seesion",
        description="复制并截取 Codex/Claude JSONL 历史，原文件保持不变。",
    )
    parser.add_argument("history", help="Codex 或 Claude JSONL 历史文件路径")
    parser.add_argument(
        "time",
        help="起始时间（包含该秒），例如 '8/20/2026, 6:09:25 PM'",
    )
    parser.add_argument("--env-file", help="指定 env 配置文件")
    parser.add_argument("--output-dir", help="临时覆盖输出目录")
    parser.add_argument("--timezone", help="临时覆盖 local 或 IANA 时区")
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = load_config(
            env_file=args.env_file,
            output_dir=args.output_dir,
            timezone_name=args.timezone,
        )
        cutoff = parse_cutoff(args.time, config.timezone_name)
        result = truncate_history(
            Path(args.history),
            cutoff,
            buffer_dir=config.buffer_dir,
            output_dir=config.output_dir,
            timezone_name=config.timezone_name,
        )
    except (OSError, ValueError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1

    print(f"已生成：{result.output}")
    print(
        f"保留 {result.selected_lines}/{result.total_lines} 行；"
        f"跳过无有效时间戳 {result.missing_timestamp_lines} 行、"
        f"无效 JSON {result.invalid_json_lines} 行。"
    )
    if result.selected_lines == 0:
        print("警告：指定时间点之后没有记录，输出文件为空。", file=sys.stderr)
    return 0
