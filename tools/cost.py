"""cost — landed cost and timing for a candidate plan leg list.

Pure arithmetic over SCENARIO_DIR/rates.json. One function: given legs, return cost,
arrival, and whether the cut-off is met. No hidden heuristics.
"""
from __future__ import annotations

import datetime as dt
import json
import os

from fastapi import APIRouter
from pydantic import BaseModel

from .common import upstream_error

router = APIRouter()


class Leg(BaseModel):
    """With option_id, mode/origin/dest/depart/arrive/rate come from the schedule and any
    values passed here are ignored (the planner cannot misstate a departure time).
    Without option_id every field must be given (ad-hoc leg)."""
    option_id: str | None = None
    mode: str | None = None  # air | truck | ocean
    origin: str | None = None
    dest: str | None = None
    depart: str | None = None
    arrive: str | None = None
    chargeable_kg: float
    rate_per_kg_usd: float | None = None


class PlanReq(BaseModel):
    awb_count: int
    cutoff: str
    legs: list[Leg]
    final_dest: str | None = None   # when given, flow is checked: kg arriving here must equal total_kg, nothing stranded en route
    total_kg: float | None = None


def _dt(v: str, field: str) -> dt.datetime:
    """Parse ISO datetime; 'Z' or offsets are converted to naive UTC so mixed inputs compare."""
    try:
        d = dt.datetime.fromisoformat(v.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as e:
        raise upstream_error("cost", f"{field}: bad ISO datetime {v!r} ({e})", status=422)
    if d.tzinfo is not None:
        d = d.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return d


def _options() -> dict:
    d = os.environ.get("SCENARIO_DIR")
    if not d:
        return {}
    try:
        with open(os.path.join(d, "options.json"), encoding="utf-8") as f:
            return {o["id"]: o for o in json.load(f)}
    except FileNotFoundError:
        return {}


def _rates() -> dict:
    d = os.environ.get("SCENARIO_DIR")
    if not d:
        raise upstream_error("cost", "SCENARIO_DIR not set", status=503)
    with open(os.path.join(d, "rates.json"), encoding="utf-8") as f:
        return json.load(f)


@router.post("/cost")
def cost(req: PlanReq):
    rates = _rates()
    opts = _options()
    resolved = []
    for leg in req.legs:
        if leg.option_id:
            o = opts.get(leg.option_id)
            if o is None:
                raise upstream_error("cost", f"unknown option_id {leg.option_id!r} (not in schedule)", status=422)
            leg = Leg(option_id=leg.option_id, mode=o["mode"], origin=o["origin"], dest=o["dest"], depart=o["depart"], arrive=o["arrive"],
                      chargeable_kg=leg.chargeable_kg, rate_per_kg_usd=o["rate_per_kg_usd"])
        else:
            missing = [f for f in ("mode", "origin", "dest", "depart", "arrive") if getattr(leg, f) is None]
            if missing:
                raise upstream_error("cost", f"ad-hoc leg needs {missing} (or give option_id)", status=422)
        resolved.append(leg)
    req.legs = resolved
    load: dict[str, float] = {}
    for leg in req.legs:
        if leg.option_id:
            load[leg.option_id] = load.get(leg.option_id, 0) + leg.chargeable_kg
    over = []
    for oid, kg in load.items():
        o = opts.get(oid)
        if o is None:
            over.append({"option_id": oid, "error": "unknown option_id (not in schedule)"})
        elif kg > o["capacity_kg"]:
            over.append({"option_id": oid, "planned_kg": kg, "capacity_kg": o["capacity_kg"], "excess_kg": kg - o["capacity_kg"]})
    total = 0.0
    breakdown = []
    for leg in req.legs:
        rate = leg.rate_per_kg_usd if leg.rate_per_kg_usd is not None else rates["default_rate_per_kg_usd"].get(leg.mode)
        if rate is None:
            raise upstream_error("cost", f"no rate for mode {leg.mode}", status=422)
        handling = rates["handling_per_awb_usd"].get(leg.mode, 0) * req.awb_count
        c = leg.chargeable_kg * rate + handling
        total += c
        breakdown.append({"leg": f"{leg.origin}->{leg.dest}", "mode": leg.mode, "freight_usd": round(leg.chargeable_kg * rate, 2), "handling_usd": handling})
    if not req.legs:
        raise upstream_error("cost", "legs is empty", status=422)
    arrive = max(_dt(l.arrive, "arrive") for l in req.legs)
    cutoff = _dt(req.cutoff, "cutoff")
    inflow: dict[str, float] = {}
    outflow: dict[str, float] = {}
    for leg in req.legs:
        inflow[leg.dest] = inflow.get(leg.dest, 0) + leg.chargeable_kg
        outflow[leg.origin] = outflow.get(leg.origin, 0) + leg.chargeable_kg
    stranded = {n: round(inflow[n] - outflow.get(n, 0), 1) for n in inflow if n not in (req.final_dest,) and inflow[n] - outflow.get(n, 0) > 0} if req.final_dest else {}
    delivered = round(inflow.get(req.final_dest, 0), 1) if req.final_dest else None
    coverage_ok = True
    if req.final_dest and req.total_kg is not None:
        coverage_ok = abs(delivered - req.total_kg) < 0.5 and not stranded
    return {"feasible": not over and arrive <= cutoff and coverage_ok, "capacity_violations": over,
            "delivered_kg_to_final_dest": delivered, "required_kg": req.total_kg, "stranded_kg_by_node": stranded, "coverage_ok": coverage_ok, "total_usd": round(total, 2), "final_arrival": arrive.isoformat() + "Z", "cutoff": cutoff.isoformat() + "Z",
            "meets_cutoff": arrive <= cutoff, "slack_hours": round((cutoff - arrive).total_seconds() / 3600, 1), "breakdown": breakdown}
