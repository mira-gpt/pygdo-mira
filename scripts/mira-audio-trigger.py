#!/usr/bin/env python3
"""Watch local microphone transcripts and wake Mira for explicit calls only."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from inotify_simple import INotify, flags

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "inqueue" / "micro1"
sys.path.insert(0, str(ROOT.parents[1]))

from gdo.mira.util import send_to_mira  # noqa: E402


MIRA_ADDRESS = re.compile(r"^mira(?:[\s:,!.?]|$)", re.IGNORECASE)


def payload_lines(ibdes: str) -> list[str]:
    """Extract visible payloads from IBDES records, ignoring blank separators."""
    lines: list[str] = []
    for line in ibdes.splitlines():
        if not line.strip():
            continue
        try:
            _prefix, payload = line.split("} ", 1)
        except ValueError:
            continue
        lines.append(payload.strip())
    return lines


def process(path: Path) -> None:
    try:
        event = json.loads(path.read_text(encoding="utf-8"))
        ibdes = str(event["ibdes"])
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Ignoring invalid audio event {path.name}: {error}", file=sys.stderr)
        path.unlink(missing_ok=True)
        return
    path.unlink(missing_ok=True)
    if any(MIRA_ADDRESS.match(line) for line in payload_lines(ibdes)):
        # Keep the full local context so $chat has the normal IBDES envelope.
        send_to_mira(f"$chat\n{ibdes}")
        print("Delivered explicit micro1 call.", flush=True)
    else:
        print("Transcript kept local; no 'mira' wake word.", flush=True)


def main() -> int:
    QUEUE.mkdir(mode=0o770, parents=True, exist_ok=True)
    print(f"Watching {QUEUE}", flush=True)
    watcher = INotify()
    watcher.add_watch(str(QUEUE), flags.MOVED_TO | flags.CLOSE_WRITE)
    while True:
        # Process a pre-existing event once after a restart, then block on
        # inotify instead of turning the microphone path into a polling loop.
        for path in sorted(QUEUE.glob("*.json")):
            process(path)
        watcher.read(timeout=60_000)


if __name__ == "__main__":
    raise SystemExit(main())
