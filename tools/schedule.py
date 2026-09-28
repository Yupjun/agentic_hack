"""schedule — flight/vessel options with remaining capacity, from the scenario files.

Airline and carrier booking APIs are not public, so capacity is SYNTHETIC and lives in
SCENARIO_DIR/options.json. The response says so in every record ("synthetic": true).
"""
from __future__ import annotations

import json
import os

from fastapi import APIRouter, Query

from .common import upstream_error

router = APIRouter()


def _load() -> list[dict]:
    d = os.environ.get("SCENARIO_DIR")
    if not d:
        raise upstream_error("schedule", "SCENARIO_DIR not set", status=503)
    with open(os.path.join(d, "options.json"), encoding="utf-8") as f:
        return json.load(f)


@router.get("/schedule")
def schedule(origin: str = Query(..., description="IATA, e.g. JFK"), dest: str | None = Query(None, description="omit to list every option departing origin"),
             mode: str | None = Query(None, description="air | truck | ocean | sea-air"),
             not_before: str | None = Query(None, description="ISO datetime; only options departing after this")):
    o, dst = origin.upper(), (dest.upper() if dest else None)
    rows = [r for r in _load() if r["origin"] == o and (dst is None or r["dest"] == dst) and (mode is None or r["mode"] == mode)]
    if not_before:
        rows = [r for r in rows if r["depart"] >= not_before]
    for r in rows:
        r["synthetic"] = True
    if not rows:
        raise upstream_error("schedule", f"no options {o}->{dst or '*'} mode={mode}", status=404)
    return {"origin": o, "dest": dst, "count": len(rows), "options": sorted(rows, key=lambda r: r["arrive"])}
