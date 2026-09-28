"""Time is ISO-8601 in specs and results, float days since spec.t0 inside the engine."""
from __future__ import annotations

import datetime as dt

UTC = dt.timezone.utc


def parse(iso: str) -> dt.datetime:
    d = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=UTC)
    return d.astimezone(UTC)


def to_day(iso: str, t0: str) -> float:
    return (parse(iso) - parse(t0)).total_seconds() / 86400.0


def from_day(day: float, t0: str) -> str:
    return (parse(t0) + dt.timedelta(days=day)).strftime("%Y-%m-%dT%H:%M:%SZ")
