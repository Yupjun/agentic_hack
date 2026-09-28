"""allocate — pack shipments into ROUTES by capacity (first-fit decreasing).

A route is a chain of option ids, e.g. ["TRK-JFK-EWR", "UAL16-0929"] (truck feeder then
flight) or ["KAL251-0929"] (single leg). Its capacity is the bottleneck of its hops; every
AWB placed on a route rides all of its hops, so the returned legs already conserve flow.

Pure mechanism: the planner names the options in the order it prefers; this tool assigns
whole AWBs (never split) to those options without exceeding remaining capacity and reports
what did not fit. Capacity comes from SCENARIO_DIR/options.json minus `already_loaded_kg`.
"""
from __future__ import annotations

import json
import os

from fastapi import APIRouter
from pydantic import BaseModel

from .common import upstream_error

router = APIRouter()


class Awb(BaseModel):
    awb: str
    chargeable_kg: float


class AllocReq(BaseModel):
    awbs: list[Awb]
    routes: list[list[str]] | None = None     # preferred order; each route = chain of option ids
    option_ids: list[str] | None = None       # shorthand: single-hop routes
    already_loaded_kg: dict[str, float] = {}  # kg already assigned to an option by earlier calls


def _options() -> dict:
    d = os.environ.get("SCENARIO_DIR")
    if not d:
        raise upstream_error("allocate", "SCENARIO_DIR not set", status=503)
    with open(os.path.join(d, "options.json"), encoding="utf-8") as f:
        return {o["id"]: o for o in json.load(f)}


@router.post("/allocate")
def allocate(req: AllocReq):
    opts = _options()
    routes = req.routes if req.routes else [[i] for i in (req.option_ids or [])]
    if not routes:
        raise upstream_error("allocate", "give routes (chains of option ids) or option_ids", status=422)
    unknown = sorted({i for r in routes for i in r if i not in opts})
    if unknown:
        raise upstream_error("allocate", f"unknown option ids {unknown}", status=422)
    for r in routes:
        for a, b in zip(r, r[1:]):
            if opts[a]["dest"] != opts[b]["origin"]:
                raise upstream_error("allocate", f"route {r}: {a} ends at {opts[a]['dest']} but {b} starts at {opts[b]['origin']}", status=422)
            if opts[b]["depart"] < opts[a]["arrive"]:
                raise upstream_error("allocate", f"route {r}: {b} departs before {a} arrives", status=422)
    room = {i: opts[i]["capacity_kg"] - req.already_loaded_kg.get(i, 0) for r in routes for i in r}
    assign: dict[str, list[dict]] = {"+".join(r): [] for r in routes}
    unplaced = []
    for a in sorted(req.awbs, key=lambda x: -x.chargeable_kg):
        for r in routes:
            if min(room[i] for i in r) >= a.chargeable_kg:
                assign["+".join(r)].append({"awb": a.awb, "chargeable_kg": a.chargeable_kg})
                for i in r:
                    room[i] -= a.chargeable_kg
                break
        else:
            unplaced.append({"awb": a.awb, "chargeable_kg": a.chargeable_kg})
    legs = []
    for r in routes:
        kg = sum(x["chargeable_kg"] for x in assign["+".join(r)])
        if kg:
            for i in r:
                legs.append({"option_id": i, "chargeable_kg": kg})
    routes_out = [{"route": "+".join(r), "kg": sum(x["chargeable_kg"] for x in assign["+".join(r)]), "awb_count": len(assign["+".join(r)]),
                   "arrive": opts[r[-1]]["arrive"], "final_dest": opts[r[-1]]["dest"], "remaining_capacity_kg": min(room[i] for i in r)} for r in routes]
    return {"plan_legs": legs, "routes": routes_out, "assignment": assign,
            "unplaced": unplaced, "unplaced_kg": sum(x["chargeable_kg"] for x in unplaced),
            "note": "plan_legs can be pasted into cost / PLAN_JSON as-is; add already_loaded_kg from earlier calls when allocating the next group"}
