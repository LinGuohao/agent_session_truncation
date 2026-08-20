# agent_session_truncation

`session` extracts Codex or Claude JSONL history from a cutoff time without modifying the source file.

## Install

Requires Python 3.11 or later.

```bash
git clone https://github.com/LinGuohao/agent_session_truncation.git
cd agent_session_truncation
python3 -m pip install -e .
```

## Usage

```bash
session /path/to/history.jsonl 8/20/2026, 6:09:25 PM
```

The source is copied to a temporary buffer, filtered, and written to the configured output directory. The buffer copy is then removed. Existing output files are never overwritten.

When the input time has no UTC offset, `SESSION_TRUNCATION_TIMEZONE=local` interprets it in the system time zone. This matches timestamps displayed by cc-switch. ISO 8601 input with an explicit offset is also supported.

## Configuration

Edit `.env`:

```dotenv
SESSION_TRUNCATION_BUFFER_DIR=./tmp
SESSION_TRUNCATION_OUTPUT_DIR=~/Downloads
SESSION_TRUNCATION_TIMEZONE=local
```

`SESSION_TRUNCATION_TIMEZONE` may also be an IANA name such as `Europe/Brussels`. Relative paths are resolved from the `.env` file location.

Use `--env-file`, `--output-dir`, or `--timezone` for per-command overrides.

## Filtering behavior

- Records with a valid top-level `timestamp` at or after the cutoff are retained.
- Original JSONL bytes and file order are preserved.
- Internal events, reasoning records, tool calls, tool outputs, attachments, and state events are retained.
- Records without a timestamp and invalid JSON lines are skipped.
- The source file is never changed.

## Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
