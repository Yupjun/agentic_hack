"""Enumerate supply candidates for a validated spec.

A candidate is one concrete way to move units of one item:
  source   S1: a stock row (already made, mfg_date known)
           S2: a production order (approved site, order day, option) -> ready day
  route    a chain of lanes (<= max_legs) from the source node to a demand node
  legs     the scheduled departures used, chosen by EARLIEST CONNECTION from a
           given first departure (waiting longer never helps arrival; capacity
           pressure is handled by starting from a later first departure, which
           is itself another candidate).

Lanes are filtered first: allowed mode, qualified (if required), carries the
item's temperature band. Routes are filtered on total exposure hours.

Shelf-life rule (grammar docstring): S1 checks remaining shelf life at RECEIPT
(arrival); S2 checks it at USE (the batch start = demand due), because a
material is consumed on that day.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from planner import timeutil as tu
from planner.grammar import PlanSpec
from planner.validate import demands_of


@dataclass
class Leg:
    lane: str
    mode: str
    frm: str
    to: str
    depart: float
    arrive: float


@dataclass
class Candidate:
    id: str
    item: str
    source: str            # "stock:<i>" or "prod:<item>:<order_day>:<option>"
    order: str | None      # MOQ group key (S2) or None
    mfg: float             # day the goods were (will be) made
    ready: float           # earliest day they may leave the source node
    legs: list[Leg]
    unit_cost: float       # per-unit production (S2 incl. premium) + per-unit lane costs
    exposure_hours: float
    start_node: str
    end_node: str
    week: int | None = None
    option: str | None = None

    @property
    def arrive(self) -> float:
        return self.legs[-1].arrive


@dataclass
class Problem:
    spec: PlanSpec
    demands: list[dict]
    candidates: list[Candidate]
    departures: dict = field(default_factory=dict)   # (lane, depart) -> capacity, fixed cost
    notes: list[str] = field(default_factory=list)


def _departures(s: PlanSpec, lane) -> list[float]:
    first = tu.to_day(lane.schedule.first, s.t0)
    return [first + k * lane.schedule.every_days for k in range(lane.schedule.count)]


def _usable_lanes(s: PlanSpec, band: str):
    c = s.constraints
    return [l for l in s.lanes if l.mode in c.allowed_modes and (l.qualified or not c.qualified_lanes_only) and band in l.temp_bands]


def _routes(lanes, src: str, dst: str, max_legs: int) -> list[list]:
    out = []

    def walk(node, path, seen):
        if len(path) > max_legs:
            return
        if node == dst and path:
            out.append(list(path))
            return
        for l in lanes:
            if l.frm == node and l.to not in seen:
                path.append(l)
                walk(l.to, path, seen | {l.to})
                path.pop()

    walk(src, [], {src})
    return out


def _chains(s: PlanSpec, route, first_depart: float, deps: dict) -> list[list[Leg]]:
    """All leg sequences from a fixed first departure where each later leg takes one of
    its first `alt_connections` feasible departures. alt=1 is earliest-connection only;
    that version could not spread a large shipment over two onward flights (found
    2026-09-28: 100 units at DXB could only use one 50-unit flight per sailing)."""
    alt = s.constraints.alt_connections
    out: list[list[Leg]] = []

    def step(i, t, acc):
        if i == len(route):
            out.append(list(acc))
            return
        l = route[i]
        if i == 0:
            choices = [first_depart]
        else:
            earliest = t + s.nodes[l.frm].min_connect_days
            choices = [x for x in deps[l.id] if x >= earliest - 1e-9][:alt]
        for d in choices:
            a = d + l.transit_days
            acc.append(Leg(l.id, l.mode, l.frm, l.to, d, a))
            step(i + 1, a, acc)
            acc.pop()

    step(0, None, [])
    return out


def build(s: PlanSpec) -> Problem:
    demands = demands_of(s)
    deps = {l.id: _departures(s, l) for l in s.lanes}
    lane_by_id = {l.id: l for l in s.lanes}
    cands: list[Candidate] = []
    notes: list[str] = []
    horizon = max(tu.to_day(d["due"], s.t0) for d in demands)
    targets = sorted({d["node"] for d in demands})

    def add_routes(item, source, order, mfg, ready, start, base_unit_cost, week=None, option=None, key="", max_wait=None):
        band = s.items[item].temp_band
        lanes = _usable_lanes(s, band)
        for dst in targets:
            for route in _routes(lanes, start, dst, s.constraints.max_legs):
                expo = sum(l.exposure_hours for l in route)
                if expo > s.constraints.max_exposure_hours + 1e-9:
                    continue
                per_unit = base_unit_cost + sum(l.cost_per_unit_usd for l in route)
                first = [d for d in deps[route[0].id] if d >= ready - 1e-9]
                # every first departure up to the horizon is a candidate (capacity may force a later one)
                seen_arrivals = set()
                for fd in first:
                    if fd > horizon:
                        break
                    if max_wait is not None and fd > ready + max_wait + 1e-9:
                        break
                    for legs in _chains(s, route, fd, deps):
                        if legs[-1].arrive > horizon + 1e-9:
                            continue
                        sig = tuple((g.lane, round(g.depart, 6)) for g in legs)
                        if sig in seen_arrivals:
                            continue
                        seen_arrivals.add(sig)
                        cid = f"{key}|" + ">".join(f"{g.lane}@{g.depart:.3f}" for g in legs)
                        cands.append(Candidate(cid, item, source, order, mfg, ready, legs, per_unit, expo, start, dst, week, option))

    if s.family == "S1":
        for i, x in enumerate(s.stock):
            add_routes(x.item, f"stock:{i}", None, tu.to_day(x.mfg_date, s.t0), tu.to_day(x.available_from, s.t0), x.node, 0.0, key=f"stock{i}")
    else:
        for x in s.production:
            o0 = max(0.0, tu.to_day(x.order_from, s.t0))
            o1 = tu.to_day(x.order_to, s.t0)
            n = int(math.floor((o1 - o0) / x.order_every_days + 1e-9)) + 1
            for k in range(n):
                od = o0 + k * x.order_every_days
                for opt in x.options:
                    ready = od + opt.lead_time_days
                    if ready > horizon:
                        continue
                    unit = x.unit_cost_usd * (1 + opt.premium_pct / 100)
                    order = f"prod:{x.item}:{od:.3f}:{opt.name}"
                    add_routes(x.item, order, order, ready, ready, x.site, unit, week=int(ready // 7), option=opt.name, key=order, max_wait=x.max_wait_days)
    used = {(g.lane, round(g.depart, 6)) for c in cands for g in c.legs}
    departures = {k: {"capacity": lane_by_id[k[0]].capacity_units, "fixed": lane_by_id[k[0]].cost_fixed_usd} for k in used}
    if not cands:
        notes.append("no candidates survived lane/temperature/exposure filters")
    return Problem(s, demands, cands, departures, notes)


def shelf_ok(s: PlanSpec, c: Candidate, d: dict) -> bool:
    it = s.items[c.item]
    check = c.arrive if s.family == "S1" else tu.to_day(d["due"], s.t0)
    remaining = c.mfg + it.shelf_life_days - check
    return remaining >= it.shelf_life_days * it.min_remaining_shelf_life_pct / 100 - 1e-9


def eligible(s: PlanSpec, c: Candidate, d: dict, slack: float) -> bool:
    return c.item == d["item"] and c.end_node == d["node"] and c.arrive <= tu.to_day(d["due"], s.t0) - slack + 1e-9 and shelf_ok(s, c, d)
