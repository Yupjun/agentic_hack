"""Append-only JSONL journal (state/journal.jsonl), one object per line, ts in UTC.

Same shape as autoresearch's journal: every run records what went in (spec_hash,
structure_key), which backend solved it, and what came out.
"""
from __future__ import annotations

import json
import os
import time

DEFAULT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "journal.jsonl")


def append(event: str, path: str | None = None, **fields) -> dict:
    row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "event": event, **fields}
    p = path or os.environ.get("CARGO_JOURNAL", DEFAULT)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    return row


def read(path: str | None = None, event: str | None = None) -> list[dict]:
    p = path or os.environ.get("CARGO_JOURNAL", DEFAULT)
    if not os.path.exists(p):
        return []
    rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    return [r for r in rows if event is None or r.get("event") == event]
