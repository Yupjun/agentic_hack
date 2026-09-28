"""Rule baselines for plan/v1 — what a planner does by hand, demand by demand.

  rule_cheapest  for each demand in due order: take eligible candidates sorted by
                 (unit cost + fixed cost spread over the lot, arrival); fill until covered.
  rule_fastest   same, sorted by (arrival, unit cost).

Both respect departure capacity, stock on hand and weekly site capacity, ship in
whole lots, and raise an order to its MOQ if it ends below (leftover). No look-ahead
across demands and no consolidation logic beyond reusing a departure already paid for.
The result has the same shape as an engine plan and is judged by the same verify.
"""
from __future__ import annotations

from collections import defaultdict

from planner import timeutil as tu
from planner.grammar import PlanSpec
from engine.options import build, eligible


def rule_plan(spec: dict, order: str) -> dict:
    s = PlanSpec.model_validate(spec)
    prob = build(s)
    cap = {k: v["capacity"] for k, v in prob.departures.items()}
    fixed = {k: v["fixed"] for k, v in prob.departures.items()}
    paid = set()
    stock_left = {f"stock:{i}": x.qty for i, x in enumerate(s.stock)}
    prod = {p.item: p for p in s.production}
    week_left = defaultdict(lambda: None)
    shipped = defaultdict(int)       # candidate id -> units
    alloc = []
    cand = {c.id: c for c in prob.candidates}
    for j, d in sorted(enumerate(prob.demands), key=lambda t: tu.parse(t[1]["due"])):
        need = d["qty"]
        pool = [c for c in prob.candidates if eligible(s, c, d, 0.0)]
        lot = s.items[d["item"]].lot_size

        def unit_fixed(c):
            return sum(fixed[(g.lane, round(g.depart, 6))] for g in c.legs if (g.lane, round(g.depart, 6)) not in paid) / max(need, lot)

        key = (lambda c: (c.unit_cost + unit_fixed(c), c.arrive)) if order == "cheapest" else (lambda c: (c.arrive, c.unit_cost + unit_fixed(c)))
        for c in sorted(pool, key=key):
            if need <= 0:
                break
            spare_on_c = shipped[c.id] - sum(a["qty"] for a in alloc if a["_cid"] == c.id)
            if spare_on_c > 0:                  # leftover from an earlier lot rounding / MOQ on this candidate
                take = min(spare_on_c, need)
                alloc.append({"_cid": c.id, "demand": d["id"], "qty": take})
                need -= take
                continue
            room = min(cap[(g.lane, round(g.depart, 6))] for g in c.legs)
            if c.source in stock_left:
                room = min(room, stock_left[c.source])
            if c.order:
                wk = (c.item, c.week)
                if week_left[wk] is None:
                    week_left[wk] = prod[c.item].capacity_per_week
                room = min(room, week_left[wk])
            units = min(room, -(-need // lot) * lot)
            units -= units % lot
            if units <= 0:
                continue
            for g in c.legs:
                k = (g.lane, round(g.depart, 6))
                cap[k] -= units
                paid.add(k)
            if c.source in stock_left:
                stock_left[c.source] -= units
            if c.order:
                week_left[(c.item, c.week)] -= units
            shipped[c.id] += units
            take = min(units, need)
            alloc.append({"_cid": c.id, "demand": d["id"], "qty": take})
            need -= take
    # MOQ: raise short orders on their first candidate (may leave stock over)
    per_order = defaultdict(int)
    first_c = {}
    for cid, q in shipped.items():
        c = cand[cid]
        if c.order:
            per_order[c.order] += q
            first_c.setdefault(c.order, cid)
    for o, q in per_order.items():
        m = prod[cand[first_c[o]].item].moq
        if q < m:
            shipped[first_c[o]] += m - q
    ships, sid = [], {}
    for cid, q in shipped.items():
        if q <= 0:
            continue
        c = cand[cid]
        sid[cid] = f"R{len(ships)+1:03d}"
        ships.append({"id": sid[cid], "candidate": cid, "item": c.item, "qty": q, "source": c.source, "option": c.option,
                      "mfg": tu.from_day(c.mfg, s.t0), "ready": tu.from_day(c.ready, s.t0),
                      "legs": [{"lane": g.lane, "mode": g.mode, "from": g.frm, "to": g.to,
                                "depart": tu.from_day(g.depart, s.t0), "arrive": tu.from_day(g.arrive, s.t0)} for g in c.legs],
                      "unit_cost_usd": round(c.unit_cost, 2)})
    allocs = [{"shipment": sid[a["_cid"]], "demand": a["demand"], "qty": a["qty"]} for a in alloc if a["_cid"] in sid]
    return {"status": "rule", "rule": order, "shipments": ships, "allocations": allocs, "cost_usd": None}
