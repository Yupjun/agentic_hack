"""validate(spec_dict) -> list[str] problems. Empty list = the spec may be run.

Checks, in order: structure (pydantic), references, time order, family rules,
and a cheap reachability / earliest-arrival lower bound so an impossible request
is refused before any solver runs (Rule of Repair: fail early, say why).
"""
from __future__ import annotations

import heapq

from pydantic import ValidationError

from . import timeutil as tu
from .grammar import PlanSpec


def parse(spec: dict) -> tuple[PlanSpec | None, list[str]]:
    try:
        return PlanSpec.model_validate(spec), []
    except ValidationError as e:
        return None, [f"structure: {'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in e.errors()]


def _iso_ok(v: str) -> bool:
    try:
        tu.parse(v)
        return True
    except (ValueError, AttributeError):
        return False


def demands_of(s: PlanSpec) -> list[dict]:
    """Expand the request into demand rows. S2: BOM x batch, plus a safety-stock row per
    material (MOS months of usage, due at the last batch start)."""
    rows = [d.model_dump() for d in s.demand]
    pp = s.production_plan
    if s.family == "S2" and pp:
        for b in pp.batches:
            for line in pp.bom:
                rows.append({"id": f"{b.id}:{line.material}", "item": line.material, "node": pp.site,
                             "qty": int(round(line.qty_per_unit * b.qty)), "due": b.start})
        last = max(pp.batches, key=lambda b: tu.parse(b.start))
        for m, usage in pp.monthly_usage.items():
            ss = int(round(pp.mos_months * usage))
            if ss > 0:
                rows.append({"id": f"safety:{m}", "item": m, "node": pp.site, "qty": ss, "due": last.start, "safety_stock": True})
    return rows


def _min_transit(s: PlanSpec, src: str, band: str | None = None) -> dict[str, float]:
    """Shortest transit (days, + connect time) from src to every node over routes the
    engine would accept: allowed mode, qualified if required, carries the band,
    at most max_legs lanes, total exposure <= max_exposure_hours. Ignores schedules.
    (First version ignored legs/exposure and passed a spec whose material had no
    usable route — found by engine/options.py on 2026-09-28.)"""
    c = s.constraints
    usable = [l for l in s.lanes if l.mode in c.allowed_modes and (l.qualified or not c.qualified_lanes_only)
              and (band is None or band in l.temp_bands)]
    best: dict[str, float] = {src: 0.0}

    def walk(node, t, legs, expo, seen):
        for l in usable:
            if l.frm != node or l.to in seen:
                continue
            e = expo + l.exposure_hours
            if legs + 1 > c.max_legs or e > c.max_exposure_hours + 1e-9:
                continue
            nt = t + l.transit_days + (s.nodes[node].min_connect_days if legs > 0 else 0)
            if nt < best.get(l.to, 1e18):
                best[l.to] = nt
            walk(l.to, nt, legs + 1, e, seen | {l.to})

    walk(src, 0.0, 0, 0.0, {src})
    return best


def validate(spec: dict) -> list[str]:
    s, probs = parse(spec)
    if s is None:
        return probs
    p: list[str] = []
    # times
    for where, v in [("t0", s.t0)] + [(f"lanes[{l.id}].schedule.first", l.schedule.first) for l in s.lanes] \
            + [(f"stock[{i}].available_from", x.available_from) for i, x in enumerate(s.stock)] \
            + [(f"stock[{i}].mfg_date", x.mfg_date) for i, x in enumerate(s.stock)] \
            + [(f"demand[{d.id}].due", d.due) for d in s.demand] \
            + [(f"production[{x.item}].order_from", x.order_from) for x in s.production] \
            + [(f"production[{x.item}].order_to", x.order_to) for x in s.production] \
            + ([(f"production_plan.batches[{b.id}].start", b.start) for b in s.production_plan.batches] if s.production_plan else []):
        if not _iso_ok(v):
            p.append(f"time: {where} is not ISO-8601: {v!r}")
    if p:
        return p
    # references
    ids = [l.id for l in s.lanes]
    if len(ids) != len(set(ids)):
        p.append("ref: duplicate lane ids")
    for l in s.lanes:
        for end in (l.frm, l.to):
            if end not in s.nodes:
                p.append(f"ref: lane {l.id} uses unknown node {end!r}")
        if l.frm == l.to:
            p.append(f"ref: lane {l.id} goes from a node to itself")
    for x in s.stock:
        if x.item not in s.items:
            p.append(f"ref: stock item {x.item!r} unknown")
        if x.node not in s.nodes:
            p.append(f"ref: stock node {x.node!r} unknown")
        if tu.parse(x.mfg_date) > tu.parse(x.available_from):
            p.append(f"time: stock {x.item} mfg_date after available_from")
    for x in s.production:
        if x.item not in s.items:
            p.append(f"ref: production item {x.item!r} unknown")
        if x.site not in s.nodes:
            p.append(f"ref: production site {x.site!r} unknown")
        if tu.parse(x.order_to) < tu.parse(x.order_from):
            p.append(f"time: production {x.item} order_to before order_from")
        names = [o.name for o in x.options]
        if len(names) != len(set(names)):
            p.append(f"ref: production {x.item} repeats an option name")
    made = [x.item for x in s.production]
    if len(made) != len(set(made)):
        p.append("family: a material has more than one production source — only the approved source is allowed (no alternate suppliers)")
    for d in s.demand:
        if d.item not in s.items:
            p.append(f"ref: demand {d.id} item {d.item!r} unknown")
        if d.node not in s.nodes:
            p.append(f"ref: demand {d.id} node {d.node!r} unknown")
    # family rules
    if s.family == "S1":
        if not s.stock:
            p.append("family: S1 needs stock")
        if not s.demand:
            p.append("family: S1 needs demand")
        if s.production or s.production_plan:
            p.append("family: S1 must not have production / production_plan")
    else:
        if not s.production or not s.production_plan:
            p.append("family: S2 needs production and production_plan")
        else:
            pp = s.production_plan
            if pp.site not in s.nodes:
                p.append(f"ref: production_plan.site {pp.site!r} unknown")
            for line in pp.bom:
                if line.material not in s.items:
                    p.append(f"ref: bom material {line.material!r} unknown")
                if line.material not in made:
                    p.append(f"ref: bom material {line.material!r} has no approved production source")
            for m in pp.monthly_usage:
                if m not in made:
                    p.append(f"ref: monthly_usage material {m!r} has no production source")
    if p:
        return p
    t0 = tu.parse(s.t0)
    for d in demands_of(s):
        if tu.parse(d["due"]) <= t0:
            p.append(f"time: demand {d['id']} due at or before t0")
    # temperature: an item needs at least one lane that carries its band
    for iid, it in s.items.items():
        if not any(it.temp_band in l.temp_bands for l in s.lanes):
            p.append(f"temp: no lane carries {iid} at {it.temp_band}")
    # reachability + earliest-arrival lower bound
    for d in demands_of(s):
        it = s.items[d["item"]]
        best = None
        if s.family == "S1":
            for x in s.stock:
                if x.item != d["item"]:
                    continue
                dist = _min_transit(s, x.node, it.temp_band)
                if d["node"] in dist:
                    eta = tu.to_day(x.available_from, s.t0) + dist[d["node"]]
                    best = eta if best is None else min(best, eta)
        else:
            for x in s.production:
                if x.item != d["item"]:
                    continue
                dist = _min_transit(s, x.site, it.temp_band)
                if d["node"] in dist:
                    eta = max(0.0, tu.to_day(x.order_from, s.t0)) + min(o.lead_time_days for o in x.options) + dist[d["node"]]
                    best = eta if best is None else min(best, eta)
        due = tu.to_day(d["due"], s.t0)
        if best is None:
            p.append(f"reach: no usable lane path to {d['node']} for demand {d['id']}")
        elif best > due + 1e-9:
            p.append(f"reach: demand {d['id']} due day {due:.1f} but earliest possible arrival is day {best:.1f}")
        # shelf life: S1 stock may already be too old to meet the receipt threshold
        if s.family == "S1":
            for x in s.stock:
                if x.item == d["item"]:
                    age_at_due = (tu.parse(d["due"]) - tu.parse(x.mfg_date)).total_seconds() / 86400
                    if age_at_due > it.shelf_life_days * (1 - it.min_remaining_shelf_life_pct / 100) and best is not None \
                            and best > tu.to_day(x.mfg_date, s.t0) + it.shelf_life_days * (1 - it.min_remaining_shelf_life_pct / 100):
                        p.append(f"shelf: stock of {x.item} cannot arrive with {it.min_remaining_shelf_life_pct}% shelf life left")
    return p
